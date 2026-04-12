export type AgentMode = {
  id: string;
  label: string;
  icon: string;
  placeholder: string;
  taskHint: string;
  quickPrompts: string[];
  description?: string;
  templates?: { name: string; image: string; emoji: string }[];
  categories?: { label: string; icon: string }[];
};

export const AGENT_MODES: AgentMode[] = [
  {
    id: "default",
    label: "Ask anything",
    icon: "sparkles",
    placeholder: "Ask Archimedes anything...",
    taskHint: "default",
    quickPrompts: [
      "Analyze this dataset and find insights",
      "Write a Python script to automate this task",
      "Research and summarize the latest AI news",
      "Help me debug this code",
    ],
  },
  {
    id: "slides",
    label: "Create slides",
    icon: "presentation",
    placeholder: "Describe your presentation topic...",
    taskHint: "plan",
    quickPrompts: [
      "Automate weekly team status reporting",
      "Build quarterly sales performance dashboard",
      "Design investor pitch deck with projections",
      "Research market opportunity for product launch",
    ],
    templates: [
      { name: "Vinyl", image: "/templates/vinyl.png", emoji: "🎷" },
      { name: "Whiteboard", image: "/templates/whiteboard.png", emoji: "🍌" },
      { name: "Grove", image: "/templates/grove.png", emoji: "🍃" },
      { name: "Urban Stories", image: "/templates/urban.png", emoji: "🏙️" },
      { name: "Art of Storytelling", image: "/templates/art.png", emoji: "🎨" },
    ],
    description: "Create professional presentations with high-fidelity templates",
  },
  {
    id: "website",
    label: "Build website",
    icon: "globe",
    placeholder: "Describe the website you want to build...",
    taskHint: "execute",
    quickPrompts: [
      "Build a SaaS landing page with pricing",
      "Create a portfolio website",
      "Make a dashboard with charts",
      "Build a corporate website",
    ],
    categories: [
      { label: "Landing Page", icon: "layout" },
      { label: "Dashboard", icon: "grid" },
      { label: "Portfolio", icon: "user" },
      { label: "Corporate", icon: "briefcase" },
      { label: "SaaS", icon: "cloud" },
    ],
    description: "Build and deploy websites with live preview",
  },
  {
    id: "research",
    label: "Wide Research",
    icon: "search",
    placeholder: "Describe a complex topic you want researched in depth...",
    taskHint: "search",
    quickPrompts: [
      "Conduct comprehensive market sizing analysis",
      "Deep competitor benchmarking study",
      "Research emerging technology landscape",
      "Investment due diligence research",
    ],
    description: "Multi-source deep research with structured reports",
  },
  {
    id: "code",
    label: "Develop apps",
    icon: "code",
    placeholder: "Describe the app you want to build...",
    taskHint: "execute",
    quickPrompts: [
      "Build fitness tracking app",
      "Create personal productivity tool",
      "Build expense reporting app",
      "Create scheduling tool with reminders",
    ],
    description: "Build full apps with code, testing and deployment",
  },
  {
    id: "spreadsheet",
    label: "Spreadsheet",
    icon: "table",
    placeholder: "Upload a spreadsheet or describe what to create...",
    taskHint: "execute",
    quickPrompts: [
      "Create financial model with projections",
      "Track personal finances with daily logs",
      "Compare top AI models using data",
      "Build project tracking spreadsheet",
    ],
    description: "Create and analyze spreadsheets and data tables",
  },
  {
    id: "visualization",
    label: "Visualization",
    icon: "chart",
    placeholder: "Upload your data and describe how to visualize it...",
    taskHint: "execute",
    quickPrompts: [
      "Build quarterly sales performance dashboard",
      "Produce supply chain efficiency report",
      "Compare SaaS pricing with charts",
      "Create interactive data visualization",
    ],
    description: "Charts, graphs, dashboards — bar, line, pie, heatmap, sankey",
  },
  {
    id: "schedule",
    label: "Schedule task",
    icon: "calendar",
    placeholder: 'Describe what to do on schedule, e.g. "send a daily market brief at 8:00am"',
    taskHint: "execute",
    quickPrompts: [
      "Monitor daily competitor news updates",
      "Generate weekly stock portfolio report",
      "Compile weekly industry trend digest",
      "Track daily social media mentions",
    ],
    description: "Autonomous recurring tasks — daily, weekly, custom schedule",
  },
  {
    id: "swarm",
    label: "Swarm Analysis",
    icon: "users",
    placeholder: "Describe your hypothesis or idea to test with public opinion simulation...",
    taskHint: "default",
    quickPrompts: [
      "Test how people would react to my new product idea",
      "Simulate public reaction to this policy proposal",
      "Analyze market reception for this startup concept",
      "Predict social media response to this campaign",
    ],
    description: "Simulate reactions from thousands of diverse personas",
  },
  {
    id: "voice",
    label: "Voice",
    icon: "mic",
    placeholder: "Type text to convert to speech, or upload audio to transcribe...",
    taskHint: "default",
    quickPrompts: [
      "Turn this article into a 3-minute audio digest",
      "Transcribe this audio recording",
      "Create podcast episode from this text",
      "Generate voiceover for my presentation",
    ],
    description: "Speech-to-text and text-to-speech (free TTS)",
  },
  {
    id: "chat",
    label: "Chat mode",
    icon: "message",
    placeholder: "Ask anything...",
    taskHint: "default",
    quickPrompts: [],
    description: "Simple conversational mode without tools",
  },
];

export const PRIMARY_MODES = ["default", "slides", "website", "research", "code"];
export const MORE_MODES = ["spreadsheet", "visualization", "schedule", "swarm", "voice", "chat"];
