// https://nuxt.com/docs/api/configuration/nuxt-config
import path from 'path';

const cors_allow_list = process.env.ALLOWED_DOMAINS
    ? process.env.ALLOWED_DOMAINS.split(',')
    : ['http://localhost:3000']
console.log("CORS Allow List: ", cors_allow_list)

export default defineNuxtConfig({
  devtools: {
    enabled: true,

    timeline: {
      enabled: true
    }
  },
  sourcemap: true,
  ssr:false,

  image: {
    dir: 'assets/images'
  },

  runtimeConfig: {
    // Private keys are only available on the server
    allowedCORSDomains: cors_allow_list,
    environment: process.env.NODE_ENV,
    // Public keys that are exposed to the client
    public: {
      apiServerURL: process.env.API_SERVER_URL || '/api',
      clerkPublicKey: process.env.CLERK_PUBLIC_KEY,
      clerkDomain: process.env.CLERK_DOMAIN,
      environment: process.env.NODE_ENV,
    }
  },

  css: ['~/assets/css/main.css', 'primeicons/primeicons.css'],

  modules: [
    "@primevue/nuxt-module",
    "@nuxtjs/tailwindcss",
    "@formkit/nuxt",
    "@vueuse/nuxt",
    "@nuxtjs/google-fonts",
    "@nuxt/content",
    "@nuxt/image",
    "nuxt-gtag",
    "@nuxt/icon",
    "@clerk/nuxt",
    "@nuxtjs/mdc"
  ],

  gtag: {
    id: process.env.GTAG_ID? process.env.GTAG_ID : 'G-XXXXXXXXXX'
  },

  primevue: {
    options: {
      unstyled: true,
      ripple: true
    },
    importPT: { from: path.resolve(__dirname, './assets/themes/primavue/presets/aura/') },
    components:{
      exclude: ["Form", "FormField", 'Editor', 'Chart']
    }
  },

  formkit: {
    // Experimental support for auto loading (see note):
    autoImport: true
  },
  nitro: {
    firebase: {
      gen: 2
    }
  },
  compatibilityDate: '2024-09-02'
})