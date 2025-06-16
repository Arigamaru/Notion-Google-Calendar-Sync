import streamlit as st

def configure_page():
    st.set_page_config(
        page_title="📅 Notion-to-Google Calendar Sync",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    st.markdown("""
        <style>
        /* General layout adjustments */
        html, body, [class*="css"]  {
            font-family: 'Segoe UI', sans-serif;
            scroll-behavior: smooth;
        }

        .block-container {
            padding: 2rem 4rem 4rem 4rem;
            max-width: 1200px;
        }

        /* Sidebar styling */
        section[data-testid="stSidebar"][aria-expanded="true"] {
            background-color: var(--sidebar-bg);
            padding: 2rem 1.5rem;
            min-width: 300px !important;
            max-width: 500px !important;
        }
        

        /* Buttons */
        .stButton > button {
            width: 100%;
            background-color: var(--button-bg);
            color: var(--button-fg);
            border: none;
            border-radius: 10px;
            padding: 0.7rem 1.5rem;
            font-size: 1rem;
            font-weight: 600;
            margin-top: 1rem;
            transition: background-color 0.3s ease;
            box-shadow: 0px 4px 10px rgba(0,0,0,0.1);
        }

        .stButton > button:hover {
            background-color: var(--button-hover);
            cursor: pointer;
        }

        /* Text inputs, selects, text areas */
        input, textarea, select {
            background-color: var(--input-bg) !important;
            color: var(--input-fg) !important;
            border-radius: 8px !important;
            border: 1px solid var(--input-border) !important;
            padding: 0.6rem !important;
            font-size: 1rem !important;
            transition: all 0.2s ease-in-out;
        }

        input:focus, textarea:focus, select:focus {
            border-color: var(--button-hover) !important;
            outline: none !important;
            box-shadow: 0 0 5px var(--button-hover) !important;
        }

        /* Headings and markdown tweaks */
        h1, h2, h3, h4 {
            font-weight: 700;
            margin-top: 2rem;
            margin-bottom: 1rem;
        }

        body {
            background-color: var(--background-color);
        }

        /* Watch for theme change and update root vars accordingly */
        </style>

        <script>
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.target && mutation.target.classList) {
                    const root = document.documentElement;
                    if (mutation.target.classList.contains("dark")) {
                        root.setAttribute("data-theme", "dark");
                    } else {
                        root.setAttribute("data-theme", "light");
                    }
                }
            });
        });

        observer.observe(document.body, { attributes: true, attributeFilter: ["class"] });
        </script>
    """, unsafe_allow_html=True)
