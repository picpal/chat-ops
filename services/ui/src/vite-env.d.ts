/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_AI_API_URL: string
  readonly VITE_CORE_API_URL: string
  readonly VITE_APP_NAME: string
  readonly VITE_APP_VERSION: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
