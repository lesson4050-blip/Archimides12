"use client";
import React from "react";

export const V1ContentRender = ({ slide, isEditMode, theme }: { slide: any, isEditMode: boolean, theme?: any }) => {
    if (!slide || !slide.content) return <div>Empty Slide</div>;

    return (
        <div className="flex flex-col items-center justify-center aspect-video h-full bg-white border border-gray-200 rounded-lg p-8 shadow-sm slide-rendered-marker">
            <h1 className="text-4xl font-bold mb-4">{slide.content.title || "No Title"}</h1>
            <p className="text-xl text-gray-700">{slide.content.description || ""}</p>
            {slide.content.bulletPoints && (
                <ul className="mt-4 list-disc pl-5">
                    {slide.content.bulletPoints.map((bp: any, i: number) => (
                        <li key={i} className="text-lg mb-2">
                            <strong>{bp.title}:</strong> {bp.description}
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
};
