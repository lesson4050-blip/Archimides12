"""
Bioinformatics API Tool — provides access to UniProt, AlphaFold DB,
and PubChem REST APIs for protein data, structure prediction, and
drug molecule lookup.

API-only design: no toy formula reimplementations. The LLM can write
gc_content/translate/complement in 3 lines via shell — wrapping them
adds zero value. What *does* add value is structured access to
biological databases that the search tool can't reliably parse.
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class BioTool:
    """
    Query biological databases: UniProt (protein), AlphaFold (3D structure),
    PubChem (drug molecules). Returns structured, parsed data.
    """

    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "bio",
                "description": (
                    "Query biological databases for molecular data. "
                    "Actions: protein_info (UniProt protein data by accession), "
                    "alphafold (predicted 3D structure links), "
                    "compound (PubChem drug/molecule lookup by name or SMILES). "
                    "Use for genomics, proteomics, drug discovery research."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["protein_info", "alphafold", "compound"],
                        },
                        "identifier": {
                            "type": "string",
                            "description": (
                                "UniProt accession (P04637), gene name, "
                                "or compound name (aspirin)"
                            ),
                        },
                        "smiles": {
                            "type": "string",
                            "description": "SMILES notation for compound lookup",
                        },
                    },
                    "required": ["action"],
                },
            },
        }

    async def execute(
        self,
        action: str,
        identifier: str = None,
        smiles: str = None,
        **kwargs,
    ) -> Dict[str, Any]:
        try:
            import httpx
        except ImportError:
            return {"success": False, "error": "httpx required: pip install httpx"}

        try:
            if action == "protein_info":
                return await self._protein_info(identifier)
            elif action == "alphafold":
                return await self._alphafold(identifier)
            elif action == "compound":
                return await self._compound(identifier, smiles)
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
        except Exception as e:
            logger.error(f"BioTool.{action} failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # ── UniProt ──────────────────────────────────────────────────────

    async def _protein_info(self, accession: Optional[str]) -> Dict[str, Any]:
        if not accession:
            return {"success": False, "error": "identifier required (UniProt accession or gene name)"}
        import httpx

        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            # Try direct accession first
            resp = await client.get(
                f"https://rest.uniprot.org/uniprotkb/{accession}",
                headers={"Accept": "application/json"},
            )
            # If 404, try search by gene name
            if resp.status_code == 400 or resp.status_code == 404:
                resp = await client.get(
                    "https://rest.uniprot.org/uniprotkb/search",
                    params={
                        "query": f"(gene:{accession}) AND (reviewed:true)",
                        "format": "json",
                        "size": "1",
                    },
                )
                if resp.status_code == 200:
                    results = resp.json().get("results", [])
                    if not results:
                        return {"success": False, "error": f"No UniProt entry for '{accession}'"}
                    data = results[0]
                else:
                    return {"success": False, "error": f"UniProt search failed: HTTP {resp.status_code}"}
            elif resp.status_code == 200:
                data = resp.json()
            else:
                return {"success": False, "error": f"UniProt API: HTTP {resp.status_code}"}

        return {"success": True, "output": self._format_uniprot(data)}

    def _format_uniprot(self, data: dict) -> str:
        """Parse UniProt JSON into readable summary."""
        acc = data.get("primaryAccession", "?")

        # Protein name
        prot_desc = data.get("proteinDescription", {})
        rec_name = prot_desc.get("recommendedName", {})
        name = rec_name.get("fullName", {}).get("value", "")
        if not name:
            sub_names = prot_desc.get("submissionNames", [{}])
            name = sub_names[0].get("fullName", {}).get("value", acc) if sub_names else acc

        # Gene
        genes = data.get("genes", [{}])
        gene = genes[0].get("geneName", {}).get("value", "—") if genes else "—"

        # Organism
        org = data.get("organism", {}).get("scientificName", "?")

        # Sequence
        seq_data = data.get("sequence", {})
        length = seq_data.get("length", "?")
        mass = seq_data.get("molWeight", 0)

        # Function
        functions = []
        for comment in data.get("comments", []):
            if comment.get("commentType") == "FUNCTION":
                for text in comment.get("texts", []):
                    functions.append(text.get("value", ""))

        # Subcellular location
        locations = []
        for comment in data.get("comments", []):
            if comment.get("commentType") == "SUBCELLULAR LOCATION":
                for sub in comment.get("subcellularLocations", []):
                    loc = sub.get("location", {}).get("value", "")
                    if loc:
                        locations.append(loc)

        lines = [
            f"═══ {name} ═══",
            f"Accession: {acc}  |  Gene: {gene}  |  Organism: {org}",
            f"Length: {length} aa  |  Mass: {mass:,} Da ({mass/1000:.1f} kDa)" if mass else f"Length: {length} aa",
            "",
        ]
        if functions:
            lines.append("Function:")
            for fn in functions:
                lines.append(f"  {fn[:500]}")
            lines.append("")
        if locations:
            lines.append(f"Location: {', '.join(locations)}")
            lines.append("")
        lines.append(f"https://www.uniprot.org/uniprot/{acc}")
        return "\n".join(lines)

    # ── AlphaFold ────────────────────────────────────────────────────

    async def _alphafold(self, accession: Optional[str]) -> Dict[str, Any]:
        if not accession:
            return {"success": False, "error": "identifier required (UniProt accession)"}
        import httpx

        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(
                f"https://alphafold.ebi.ac.uk/api/prediction/{accession}"
            )
            if resp.status_code != 200:
                # Construct links anyway — they may still work
                return {
                    "success": True,
                    "output": (
                        f"AlphaFold prediction for {accession}:\n"
                        f"  View:  https://alphafold.ebi.ac.uk/entry/{accession}\n"
                        f"  PDB:   https://alphafold.ebi.ac.uk/files/AF-{accession}-F1-model_v4.pdb\n"
                        f"  CIF:   https://alphafold.ebi.ac.uk/files/AF-{accession}-F1-model_v4.cif\n"
                        f"  (API returned {resp.status_code} — links may still be valid)"
                    ),
                }

            entries = resp.json()
            if not entries:
                return {"success": False, "error": f"No AlphaFold prediction for {accession}"}

            entry = entries[0] if isinstance(entries, list) else entries
            pdb_url = entry.get("pdbUrl", "")
            cif_url = entry.get("cifUrl", "")
            pae_url = entry.get("paeImageUrl", "")
            confidence = entry.get("confidenceAvg", "?")
            version = entry.get("latestVersion", "?")

            return {
                "success": True,
                "output": (
                    f"AlphaFold prediction for {accession} (v{version}):\n"
                    f"  Avg confidence (pLDDT): {confidence}\n"
                    f"  View:  https://alphafold.ebi.ac.uk/entry/{accession}\n"
                    f"  PDB:   {pdb_url}\n"
                    f"  CIF:   {cif_url}\n"
                    f"  PAE:   {pae_url}\n"
                    f"  Download: wget '{pdb_url}' -O {accession}.pdb"
                ),
            }

    # ── PubChem ──────────────────────────────────────────────────────

    async def _compound(
        self, name: Optional[str], smiles: Optional[str]
    ) -> Dict[str, Any]:
        if not name and not smiles:
            return {"success": False, "error": "identifier or smiles required"}
        import httpx

        async with httpx.AsyncClient(timeout=15) as client:
            if smiles:
                encoded = smiles.replace("#", "%23").replace("+", "%2B")
                url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/{encoded}/JSON"
            else:
                url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{name}/JSON"

            resp = await client.get(url)
            if resp.status_code != 200:
                return {"success": False, "error": f"PubChem: HTTP {resp.status_code} for '{name or smiles}'"}

            data = resp.json()
            compounds = data.get("PC_Compounds", [])
            if not compounds:
                return {"success": False, "error": f"No PubChem compound for '{name or smiles}'"}

            return {"success": True, "output": self._format_pubchem(compounds[0], name or smiles)}

    def _format_pubchem(self, compound: dict, query: str) -> str:
        cid = compound.get("id", {}).get("id", {}).get("cid", "?")
        props = {}
        for prop in compound.get("props", []):
            label = prop.get("urn", {}).get("label", "")
            name_field = prop.get("urn", {}).get("name", "")
            val = prop.get("value", {})
            value = val.get("sval", val.get("fval", val.get("ival", "")))
            key = f"{label}" if not name_field else f"{label} ({name_field})"
            if value and label in (
                "Molecular Formula", "Molecular Weight", "IUPAC Name",
                "InChI", "SMILES", "Log P", "Exact Mass",
                "Topological Polar Surface Area",
            ):
                props[key] = value

        lines = [f"═══ PubChem: {query} (CID {cid}) ═══"]
        for k, v in props.items():
            lines.append(f"  {k}: {v}")
        lines.append(f"\nhttps://pubchem.ncbi.nlm.nih.gov/compound/{cid}")
        return "\n".join(lines)
