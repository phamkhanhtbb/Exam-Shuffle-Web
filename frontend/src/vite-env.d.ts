/// <reference types="vite/client" />

interface ImportMetaEnv {
    /** API base URL, e.g. https://api.trondeonline.me */
    readonly VITE_API_URL: string;
}

interface ImportMeta {
    readonly env: ImportMetaEnv;
}
