"""
Connector Registry: defines what each service can DO
and maps capabilities to tool functions.
This is what Archimedes uses to understand connected services.
"""
from typing import Dict, List, Any


# Full catalog of 80+ services
# Each entry: id, name, category, nango_key, capabilities, icon
CONNECTOR_CATALOG = {
    # ─── DEV TOOLS ──────────────────────────────
    "github": {
        "name": "GitHub", "icon": "🐙", "category": "dev",
        "nango_key": "github",
        "description": "Repos, issues, PRs, code, gists",
        "auth_type": "oauth",
        "capabilities": [
            "clone_repo", "list_repos", "read_file", "create_file",
            "update_file", "delete_file", "list_issues", "create_issue",
            "close_issue", "list_prs", "create_pr", "merge_pr",
            "list_commits", "create_branch", "push_file", "fork_repo"
        ]
    },
    "gitlab": {
        "name": "GitLab", "icon": "🦊", "category": "dev",
        "nango_key": "gitlab",
        "description": "Repos, CI/CD, merge requests",
        "auth_type": "oauth",
        "capabilities": ["list_repos", "list_mrs", "create_mr", "read_file"]
    },
    "vercel": {
        "name": "Vercel", "icon": "▲", "category": "dev",
        "nango_key": "vercel",
        "description": "Deploy and manage projects",
        "auth_type": "token",
        "capabilities": [
            "list_projects", "list_deployments", "trigger_deploy",
            "get_logs", "set_env_var", "delete_project"
        ]
    },
    "supabase": {
        "name": "Supabase", "icon": "⚡", "category": "dev",
        "nango_key": "supabase",
        "description": "Database, auth, storage",
        "auth_type": "token",
        "capabilities": [
            "run_query", "insert_row", "update_row", "delete_row",
            "list_tables", "list_users", "upload_file"
        ]
    },
    "aws": {
        "name": "AWS", "icon": "☁️", "category": "dev",
        "nango_key": "aws",
        "description": "S3, Lambda, EC2 basics",
        "auth_type": "token",
        "capabilities": [
            "s3_upload", "s3_download", "s3_list",
            "lambda_invoke", "ec2_list"
        ]
    },
    "render": {
        "name": "Render", "icon": "🟣", "category": "dev",
        "nango_key": "render",
        "description": "Deploy web services",
        "auth_type": "token",
        "capabilities": ["list_services", "trigger_deploy", "get_logs"]
    },
    "railway": {
        "name": "Railway", "icon": "🚂", "category": "dev",
        "nango_key": "railway",
        "description": "Deploy apps instantly",
        "auth_type": "token",
        "capabilities": ["list_projects", "trigger_deploy", "get_logs"]
    },
    "npm": {
        "name": "npm", "icon": "📦", "category": "dev",
        "nango_key": "npm",
        "description": "Package registry",
        "auth_type": "token",
        "capabilities": ["search_package", "get_package_info", "publish"]
    },
    "docker_hub": {
        "name": "Docker Hub", "icon": "🐳", "category": "dev",
        "nango_key": "docker-hub",
        "description": "Container registry",
        "auth_type": "token",
        "capabilities": ["list_repos", "pull_image", "push_image"]
    },
    "linear": {
        "name": "Linear", "icon": "📐", "category": "dev",
        "nango_key": "linear",
        "description": "Issue tracking for dev teams",
        "auth_type": "oauth",
        "capabilities": [
            "list_issues", "create_issue", "update_issue",
            "list_projects", "list_cycles", "assign_issue"
        ]
    },
    "jira": {
        "name": "Jira", "icon": "🔵", "category": "dev",
        "nango_key": "jira",
        "description": "Project management",
        "auth_type": "oauth",
        "capabilities": [
            "list_issues", "create_issue", "update_issue",
            "list_sprints", "add_comment", "transition_issue"
        ]
    },
    "sentry": {
        "name": "Sentry", "icon": "🔴", "category": "dev",
        "nango_key": "sentry",
        "description": "Error monitoring",
        "auth_type": "token",
        "capabilities": ["list_issues", "get_issue", "resolve_issue"]
    },

    # ─── COMMUNICATION ───────────────────────────
    "gmail": {
        "name": "Gmail", "icon": "📧", "category": "communication",
        "nango_key": "google-mail",
        "description": "Read, send, search emails",
        "auth_type": "oauth",
        "capabilities": [
            "read_emails", "send_email", "search_emails",
            "reply_email", "forward_email", "delete_email",
            "list_labels", "create_label", "mark_read"
        ]
    },
    "slack": {
        "name": "Slack", "icon": "💬", "category": "communication",
        "nango_key": "slack",
        "description": "Messages, channels, files",
        "auth_type": "oauth",
        "capabilities": [
            "send_message", "read_channel", "list_channels",
            "upload_file", "create_channel", "invite_user",
            "get_user_info", "react_message", "list_messages"
        ]
    },
    "discord": {
        "name": "Discord", "icon": "🎮", "category": "communication",
        "nango_key": "discord",
        "description": "Messages, servers, bots",
        "auth_type": "oauth",
        "capabilities": [
            "send_message", "read_messages", "list_channels",
            "create_channel", "ban_user", "list_members"
        ]
    },
    "telegram": {
        "name": "Telegram", "icon": "✈️", "category": "communication",
        "nango_key": "telegram",
        "description": "Bot API — send messages",
        "auth_type": "token",
        "capabilities": [
            "send_message", "send_photo", "send_document",
            "get_updates", "create_poll"
        ]
    },
    "whatsapp": {
        "name": "WhatsApp", "icon": "📱", "category": "communication",
        "nango_key": "whatsapp",
        "description": "WhatsApp Business API",
        "auth_type": "token",
        "capabilities": ["send_message", "send_template", "get_media"]
    },
    "microsoft_teams": {
        "name": "Microsoft Teams", "icon": "🟦", "category": "communication",
        "nango_key": "microsoft-teams",
        "description": "Teams messages and channels",
        "auth_type": "oauth",
        "capabilities": ["send_message", "read_messages", "list_channels"]
    },
    "sendgrid": {
        "name": "SendGrid", "icon": "📮", "category": "communication",
        "nango_key": "sendgrid",
        "description": "Transactional email",
        "auth_type": "token",
        "capabilities": [
            "send_email", "send_bulk", "get_stats",
            "manage_templates", "manage_contacts"
        ]
    },
    "twilio": {
        "name": "Twilio", "icon": "📞", "category": "communication",
        "nango_key": "twilio",
        "description": "SMS, calls, WhatsApp",
        "auth_type": "token",
        "capabilities": [
            "send_sms", "make_call", "send_whatsapp",
            "list_messages", "list_calls"
        ]
    },
    "intercom": {
        "name": "Intercom", "icon": "💭", "category": "communication",
        "nango_key": "intercom",
        "description": "Customer messaging",
        "auth_type": "oauth",
        "capabilities": [
            "list_conversations", "reply_conversation",
            "list_contacts", "create_contact", "send_message"
        ]
    },
    "zendesk": {
        "name": "Zendesk", "icon": "🎫", "category": "communication",
        "nango_key": "zendesk",
        "description": "Support tickets",
        "auth_type": "oauth",
        "capabilities": [
            "list_tickets", "create_ticket", "update_ticket",
            "add_comment", "list_users", "assign_ticket"
        ]
    },
    "mailchimp": {
        "name": "Mailchimp", "icon": "🐒", "category": "communication",
        "nango_key": "mailchimp",
        "description": "Email marketing",
        "auth_type": "oauth",
        "capabilities": [
            "list_campaigns", "create_campaign", "send_campaign",
            "list_subscribers", "add_subscriber", "remove_subscriber"
        ]
    },

    # ─── PRODUCTIVITY ────────────────────────────
    "notion": {
        "name": "Notion", "icon": "📝", "category": "productivity",
        "nango_key": "notion",
        "description": "Pages, databases, blocks",
        "auth_type": "oauth",
        "capabilities": [
            "read_page", "create_page", "update_page", "delete_block",
            "query_database", "create_database_entry", "search_pages",
            "list_databases", "append_blocks"
        ]
    },
    "google_drive": {
        "name": "Google Drive", "icon": "📁", "category": "productivity",
        "nango_key": "google-drive",
        "description": "Files, folders, docs",
        "auth_type": "oauth",
        "capabilities": [
            "list_files", "download_file", "upload_file",
            "create_folder", "delete_file", "share_file",
            "search_files", "move_file", "copy_file"
        ]
    },
    "google_docs": {
        "name": "Google Docs", "icon": "📄", "category": "productivity",
        "nango_key": "google-docs",
        "description": "Create and edit documents",
        "auth_type": "oauth",
        "capabilities": [
            "read_doc", "create_doc", "update_doc",
            "append_text", "export_pdf"
        ]
    },
    "google_sheets": {
        "name": "Google Sheets", "icon": "📊", "category": "productivity",
        "nango_key": "google-sheets",
        "description": "Spreadsheets and data",
        "auth_type": "oauth",
        "capabilities": [
            "read_sheet", "write_cell", "append_row", "create_sheet",
            "delete_row", "get_range", "format_cells"
        ]
    },
    "google_calendar": {
        "name": "Google Calendar", "icon": "📅", "category": "productivity",
        "nango_key": "google-calendar",
        "description": "Events, reminders, meetings",
        "auth_type": "oauth",
        "capabilities": [
            "list_events", "create_event", "update_event",
            "delete_event", "accept_invite", "list_calendars"
        ]
    },
    "airtable": {
        "name": "Airtable", "icon": "🟦", "category": "productivity",
        "nango_key": "airtable",
        "description": "Database spreadsheet hybrid",
        "auth_type": "token",
        "capabilities": [
            "list_records", "create_record", "update_record",
            "delete_record", "list_tables", "search_records"
        ]
    },
    "asana": {
        "name": "Asana", "icon": "⭕", "category": "productivity",
        "nango_key": "asana",
        "description": "Project and task management",
        "auth_type": "oauth",
        "capabilities": [
            "list_tasks", "create_task", "update_task", "complete_task",
            "list_projects", "add_subtask", "list_teams"
        ]
    },
    "trello": {
        "name": "Trello", "icon": "🟧", "category": "productivity",
        "nango_key": "trello",
        "description": "Kanban boards",
        "auth_type": "token",
        "capabilities": [
            "list_boards", "list_cards", "create_card",
            "move_card", "update_card", "add_comment"
        ]
    },
    "clickup": {
        "name": "ClickUp", "icon": "🟣", "category": "productivity",
        "nango_key": "clickup",
        "description": "All-in-one productivity",
        "auth_type": "oauth",
        "capabilities": [
            "list_tasks", "create_task", "update_task",
            "list_spaces", "list_folders"
        ]
    },
    "todoist": {
        "name": "Todoist", "icon": "✅", "category": "productivity",
        "nango_key": "todoist",
        "description": "Task management",
        "auth_type": "oauth",
        "capabilities": [
            "list_tasks", "create_task", "complete_task",
            "list_projects", "create_project"
        ]
    },
    "dropbox": {
        "name": "Dropbox", "icon": "📦", "category": "productivity",
        "nango_key": "dropbox",
        "description": "File storage and sharing",
        "auth_type": "oauth",
        "capabilities": [
            "list_files", "download_file", "upload_file",
            "delete_file", "create_folder", "share_file"
        ]
    },
    "onedrive": {
        "name": "OneDrive", "icon": "☁️", "category": "productivity",
        "nango_key": "microsoft-onedrive",
        "description": "Microsoft file storage",
        "auth_type": "oauth",
        "capabilities": [
            "list_files", "download_file", "upload_file",
            "delete_file", "create_folder"
        ]
    },
    "confluence": {
        "name": "Confluence", "icon": "📚", "category": "productivity",
        "nango_key": "confluence",
        "description": "Team wiki and docs",
        "auth_type": "oauth",
        "capabilities": [
            "read_page", "create_page", "update_page",
            "search_pages", "list_spaces"
        ]
    },
    "obsidian": {
        "name": "Obsidian", "icon": "💜", "category": "productivity",
        "nango_key": "obsidian",
        "description": "Local knowledge base",
        "auth_type": "token",
        "capabilities": ["read_note", "create_note", "search_notes"]
    },

    # ─── CRM & SALES ─────────────────────────────
    "hubspot": {
        "name": "HubSpot", "icon": "🔶", "category": "sales",
        "nango_key": "hubspot",
        "description": "CRM, contacts, deals",
        "auth_type": "oauth",
        "capabilities": [
            "list_contacts", "create_contact", "update_contact",
            "list_deals", "create_deal", "update_deal",
            "list_companies", "send_email", "create_note",
            "list_tickets", "get_analytics"
        ]
    },
    "salesforce": {
        "name": "Salesforce", "icon": "☁️", "category": "sales",
        "nango_key": "salesforce",
        "description": "Enterprise CRM",
        "auth_type": "oauth",
        "capabilities": [
            "list_contacts", "create_contact", "list_opportunities",
            "create_opportunity", "run_soql", "create_task"
        ]
    },
    "pipedrive": {
        "name": "Pipedrive", "icon": "🟢", "category": "sales",
        "nango_key": "pipedrive",
        "description": "Sales pipeline",
        "auth_type": "oauth",
        "capabilities": [
            "list_deals", "create_deal", "update_deal",
            "list_contacts", "create_activity"
        ]
    },
    "close": {
        "name": "Close CRM", "icon": "📌", "category": "sales",
        "nango_key": "close",
        "description": "Sales CRM for startups",
        "auth_type": "token",
        "capabilities": ["list_leads", "create_lead", "log_call"]
    },

    # ─── FINANCE ─────────────────────────────────
    "stripe": {
        "name": "Stripe", "icon": "💳", "category": "finance",
        "nango_key": "stripe",
        "description": "Payments, subscriptions",
        "auth_type": "token",
        "capabilities": [
            "list_customers", "create_customer", "list_payments",
            "create_payment_link", "list_subscriptions",
            "cancel_subscription", "get_balance", "create_invoice",
            "list_products", "create_product", "create_refund"
        ]
    },
    "quickbooks": {
        "name": "QuickBooks", "icon": "💰", "category": "finance",
        "nango_key": "quickbooks",
        "description": "Accounting software",
        "auth_type": "oauth",
        "capabilities": [
            "list_invoices", "create_invoice", "list_expenses",
            "list_customers", "get_reports"
        ]
    },
    "xero": {
        "name": "Xero", "icon": "🔵", "category": "finance",
        "nango_key": "xero",
        "description": "Accounting and invoicing",
        "auth_type": "oauth",
        "capabilities": [
            "list_invoices", "create_invoice", "list_contacts",
            "get_balance_sheet"
        ]
    },
    "paypal": {
        "name": "PayPal", "icon": "🅿️", "category": "finance",
        "nango_key": "paypal",
        "description": "Payments and transfers",
        "auth_type": "oauth",
        "capabilities": ["list_transactions", "create_invoice", "get_balance"]
    },

    # ─── MARKETING ───────────────────────────────
    "twitter": {
        "name": "Twitter/X", "icon": "🐦", "category": "social",
        "nango_key": "twitter",
        "description": "Tweets and social",
        "auth_type": "oauth",
        "capabilities": [
            "post_tweet", "reply_tweet", "like_tweet",
            "retweet", "search_tweets", "get_profile",
            "list_followers", "send_dm"
        ]
    },
    "linkedin": {
        "name": "LinkedIn", "icon": "💼", "category": "social",
        "nango_key": "linkedin",
        "description": "Professional network",
        "auth_type": "oauth",
        "capabilities": [
            "post_content", "get_profile", "list_connections",
            "send_message"
        ]
    },
    "instagram": {
        "name": "Instagram", "icon": "📸", "category": "social",
        "nango_key": "instagram",
        "description": "Posts and stories",
        "auth_type": "oauth",
        "capabilities": [
            "list_media", "get_profile", "get_insights",
            "list_comments"
        ]
    },
    "facebook": {
        "name": "Facebook", "icon": "📘", "category": "social",
        "nango_key": "facebook",
        "description": "Pages and ads",
        "auth_type": "oauth",
        "capabilities": [
            "list_posts", "create_post", "get_page_insights",
            "list_ads"
        ]
    },
    "youtube": {
        "name": "YouTube", "icon": "▶️", "category": "social",
        "nango_key": "youtube",
        "description": "Videos and analytics",
        "auth_type": "oauth",
        "capabilities": [
            "list_videos", "get_video_stats", "list_comments",
            "search_videos", "list_playlists"
        ]
    },
    "google_ads": {
        "name": "Google Ads", "icon": "📢", "category": "marketing",
        "nango_key": "google-ads",
        "description": "Ad campaigns",
        "auth_type": "oauth",
        "capabilities": ["list_campaigns", "get_metrics", "pause_campaign"]
    },

    # ─── AI & DATA ───────────────────────────────
    "openai": {
        "name": "OpenAI", "icon": "🤖", "category": "ai",
        "nango_key": "openai",
        "description": "GPT, Whisper, DALL-E",
        "auth_type": "token",
        "capabilities": ["chat", "generate_image", "transcribe", "embed"]
    },
    "anthropic": {
        "name": "Anthropic", "icon": "🧠", "category": "ai",
        "nango_key": "anthropic",
        "description": "Claude models",
        "auth_type": "token",
        "capabilities": ["chat", "analyze_image"]
    },
    "groq": {
        "name": "Groq", "icon": "⚡", "category": "ai",
        "nango_key": "groq",
        "description": "Ultra-fast inference",
        "auth_type": "token",
        "capabilities": ["chat", "transcribe"]
    },
    "elevenlabs": {
        "name": "ElevenLabs", "icon": "🎙️", "category": "ai",
        "nango_key": "elevenlabs",
        "description": "Text-to-speech",
        "auth_type": "token",
        "capabilities": ["generate_voice", "list_voices", "clone_voice"]
    },
    "replicate": {
        "name": "Replicate", "icon": "🔁", "category": "ai",
        "nango_key": "replicate",
        "description": "Run ML models",
        "auth_type": "token",
        "capabilities": ["run_model", "list_models", "get_prediction"]
    },
    "stability": {
        "name": "Stability AI", "icon": "🎨", "category": "ai",
        "nango_key": "stability",
        "description": "Image generation",
        "auth_type": "token",
        "capabilities": ["generate_image", "upscale_image", "edit_image"]
    },
    "pinecone": {
        "name": "Pinecone", "icon": "🌲", "category": "ai",
        "nango_key": "pinecone",
        "description": "Vector database",
        "auth_type": "token",
        "capabilities": ["upsert", "query", "delete", "list_indexes"]
    },
    "tavily": {
        "name": "Tavily", "icon": "🔍", "category": "ai",
        "nango_key": "tavily",
        "description": "AI web search",
        "auth_type": "token",
        "capabilities": ["search", "get_answer", "extract_content"]
    },

    # ─── E-COMMERCE ──────────────────────────────
    "shopify": {
        "name": "Shopify", "icon": "🛍️", "category": "ecommerce",
        "nango_key": "shopify",
        "description": "Orders, products, customers",
        "auth_type": "oauth",
        "capabilities": [
            "list_products", "create_product", "update_product",
            "list_orders", "update_order", "list_customers",
            "get_analytics", "create_discount"
        ]
    },
    "woocommerce": {
        "name": "WooCommerce", "icon": "🟣", "category": "ecommerce",
        "nango_key": "woocommerce",
        "description": "WordPress e-commerce",
        "auth_type": "token",
        "capabilities": [
            "list_products", "create_product", "list_orders",
            "update_order", "list_customers"
        ]
    },
    "amazon_seller": {
        "name": "Amazon Seller", "icon": "📦", "category": "ecommerce",
        "nango_key": "amazon",
        "description": "Amazon marketplace",
        "auth_type": "oauth",
        "capabilities": [
            "list_orders", "get_inventory", "update_price",
            "get_reports"
        ]
    },

    # ─── DESIGN ──────────────────────────────────
    "figma": {
        "name": "Figma", "icon": "🎨", "category": "design",
        "nango_key": "figma",
        "description": "Design files and components",
        "auth_type": "oauth",
        "capabilities": [
            "list_files", "get_file", "list_components",
            "export_image", "get_comments", "add_comment"
        ]
    },
    "canva": {
        "name": "Canva", "icon": "🖌️", "category": "design",
        "nango_key": "canva",
        "description": "Designs and presentations",
        "auth_type": "oauth",
        "capabilities": ["list_designs", "create_design", "export_design"]
    },

    # ─── ANALYTICS ───────────────────────────────
    "google_analytics": {
        "name": "Google Analytics", "icon": "📈", "category": "analytics",
        "nango_key": "google-analytics",
        "description": "Web analytics",
        "auth_type": "oauth",
        "capabilities": [
            "get_sessions", "get_pageviews", "get_top_pages",
            "get_traffic_source", "get_conversions"
        ]
    },
    "mixpanel": {
        "name": "Mixpanel", "icon": "📊", "category": "analytics",
        "nango_key": "mixpanel",
        "description": "Product analytics",
        "auth_type": "token",
        "capabilities": [
            "track_event", "get_funnel", "get_retention",
            "list_events", "get_user_properties"
        ]
    },
    "amplitude": {
        "name": "Amplitude", "icon": "📉", "category": "analytics",
        "nango_key": "amplitude",
        "description": "Product analytics",
        "auth_type": "token",
        "capabilities": ["get_events", "get_user_activity", "get_cohorts"]
    },

    # ─── DATABASES ───────────────────────────────
    "mongodb": {
        "name": "MongoDB Atlas", "icon": "🍃", "category": "database",
        "nango_key": "mongodb",
        "description": "NoSQL database",
        "auth_type": "token",
        "capabilities": [
            "find", "insert_one", "insert_many", "update_one",
            "delete_one", "aggregate", "list_collections"
        ]
    },
    "redis": {
        "name": "Redis Cloud", "icon": "🔴", "category": "database",
        "nango_key": "redis",
        "description": "Key-value cache",
        "auth_type": "token",
        "capabilities": ["get", "set", "delete", "list_keys", "expire"]
    },
    "planetscale": {
        "name": "PlanetScale", "icon": "🪐", "category": "database",
        "nango_key": "planetscale",
        "description": "MySQL-compatible database",
        "auth_type": "token",
        "capabilities": ["run_query", "list_databases", "list_tables"]
    },

    # ─── HR & OPERATIONS ────────────────────────
    "calendly": {
        "name": "Calendly", "icon": "📅", "category": "operations",
        "nango_key": "calendly",
        "description": "Scheduling and bookings",
        "auth_type": "oauth",
        "capabilities": [
            "list_events", "get_availability", "cancel_event",
            "list_event_types"
        ]
    },
    "zoom": {
        "name": "Zoom", "icon": "🎥", "category": "operations",
        "nango_key": "zoom",
        "description": "Video meetings",
        "auth_type": "oauth",
        "capabilities": [
            "create_meeting", "list_meetings", "get_recording",
            "delete_meeting", "get_participants"
        ]
    },
    "google_meet": {
        "name": "Google Meet", "icon": "🟢", "category": "operations",
        "nango_key": "google-meet",
        "description": "Google video calls",
        "auth_type": "oauth",
        "capabilities": ["create_meeting", "list_meetings"]
    },
    "harvest": {
        "name": "Harvest", "icon": "⏱️", "category": "operations",
        "nango_key": "harvest",
        "description": "Time tracking",
        "auth_type": "oauth",
        "capabilities": [
            "list_time_entries", "create_time_entry",
            "list_projects", "get_reports"
        ]
    },
    "bamboohr": {
        "name": "BambooHR", "icon": "🎋", "category": "operations",
        "nango_key": "bamboohr",
        "description": "HR management",
        "auth_type": "token",
        "capabilities": [
            "list_employees", "get_employee", "list_time_off",
            "approve_time_off"
        ]
    },
    "workday": {
        "name": "Workday", "icon": "💼", "category": "operations",
        "nango_key": "workday",
        "description": "Enterprise HR",
        "auth_type": "oauth",
        "capabilities": ["list_employees", "get_org_chart", "list_jobs"]
    },
}

# Category metadata
CATEGORIES = {
    "dev": {"name": "Developer Tools", "icon": "⚙️"},
    "communication": {"name": "Communication", "icon": "💬"},
    "productivity": {"name": "Productivity", "icon": "📋"},
    "sales": {"name": "CRM & Sales", "icon": "🤝"},
    "finance": {"name": "Finance", "icon": "💰"},
    "social": {"name": "Social Media", "icon": "📱"},
    "marketing": {"name": "Marketing", "icon": "📢"},
    "ai": {"name": "AI & Data", "icon": "🧠"},
    "ecommerce": {"name": "E-Commerce", "icon": "🛍️"},
    "design": {"name": "Design", "icon": "🎨"},
    "analytics": {"name": "Analytics", "icon": "📊"},
    "database": {"name": "Databases", "icon": "🗄️"},
    "operations": {"name": "Operations", "icon": "⚙️"},
}
