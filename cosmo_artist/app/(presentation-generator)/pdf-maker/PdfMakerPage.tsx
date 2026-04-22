"use client";
import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { RootState } from "@/store/store";
import { setPresentationData } from "@/store/slices/presentationGeneration";
import { DashboardApi } from "../services/api/dashboard";
import { PresentationLayoutRenderer } from "../components/PresentationLayoutRenderer";

const PresentationPage = ({ presentation_id }: { presentation_id: string }) => {
  const [contentLoading, setContentLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const dispatch = useDispatch();
  const { presentationData } = useSelector((state: RootState) => state.presentationGeneration);

  useEffect(() => {
    const fetchData = async () => {
      console.log(`BROWSER: Starting fetch for presentation: ${presentation_id}`);
      try {
        const data = await DashboardApi.getPresentation(presentation_id);
        if (!data) throw new Error("No data received from API");
        
        console.log("BROWSER: Presentation data loaded successfully.");
        dispatch(setPresentationData(data));
        setContentLoading(false);
      } catch (err: any) {
        console.error("BROWSER ERROR: Fetch failed:", err.message);
        setError(err.message);
        setContentLoading(false);
      }
    };
    fetchData();
  }, [presentation_id, dispatch]);

  if (error) return (
    <div className="p-20 text-red-600 bg-red-50 border border-red-200 rounded">
      <h1 className="text-xl font-bold">BROWSER RENDER ERROR</h1>
      <p>{error}</p>
    </div>
  );

  if (contentLoading || !presentationData) return <div className="p-20 text-gray-500">BROWSER: Loading slides...</div>;

  return (
    <div id="presentation-slides-wrapper" className="flex flex-col items-center bg-[#1a1a1a] py-20 gap-20 min-h-screen">
      {presentationData.slides?.map((slide: any, index: number) => (
        <div 
          key={index} 
          id={`slide-${index}`} 
          className="w-[1280px] h-[720px] slide-rendered-marker bg-white shadow-2xl relative overflow-hidden shrink-0" 
          data-speaker-note={slide.speaker_note}
        >
          <PresentationLayoutRenderer slide={slide} />
        </div>
      ))}
    </div>
  );
};
export default PresentationPage;

