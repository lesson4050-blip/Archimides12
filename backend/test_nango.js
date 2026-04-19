const { Nango } = require('@nangohq/node');

const nango = new Nango({ secretKey: 'ff90da3e-037f-47de-a6bb-fc56a12eada9', host: 'http://localhost:3003' });

async function createSess() {
    try {
        const token = await nango.createConnectSession({
            connectionId: "default"
        });
        console.log("SUCCESS TOKEN:", token);
    } catch (e) {
        console.error("SDK ERROR:", e.response ? e.response.data : e.message);
    }
}
createSess();
