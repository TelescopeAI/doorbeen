import { clerkPlugin } from 'vue-clerk'
import type { AuthObject } from '@clerk/backend/internal'

export default defineNuxtPlugin((nuxtApp) => {
    const runtimeConfig = useRuntimeConfig()
    const publishableKey = runtimeConfig.public.clerkPublicKey
    const allowed_origins = runtimeConfig.public.clerkAllowedOrigins
    const serverInitialState = useState<AuthObject | undefined>('clerk-initial-state', () => undefined)

    // Installing the `withClerkMiddleware` from `h3-clerk` adds an `auth` object to the context.
    // We can then use the `auth` object to get the initial state of the user.
    if (import.meta.server) {
        const authContext = useRequestEvent()?.context.auth
        serverInitialState.value = authContext ? pruneUnserializableFields(authContext) : undefined
    }
    const plugin_options = {
        publishableKey,
        routerPush: (to: string) => navigateTo(to),
        routerReplace: (to: string) => navigateTo(to, { replace: true }),
        initialState: serverInitialState.value,
        domain: runtimeConfig.public.clerkDomain,
        // signInForceRedirectUrl: '/auth/login',
        // signUpForceRedirectUrl: '/',
        signInUrl: '/auth/login',
        afterSignInUrl: "/",
        afterSignUpUrl: "/",
        supportEmail: "info@jointelescope.com",
        allowed_origins: allowed_origins,
        // appearance: {
        //     variables: { colorPrimary: '#000000' },
        //     elements: {
        //         formButtonPrimary:
        //             'bg-black border border-black border-solid hover:bg-white hover:text-black',
        //         socialButtonsBlockButton:
        //             'bg-white border-gray-200 hover:bg-transparent hover:border-black text-gray-600 hover:text-black',
        //         socialButtonsBlockButtonText: 'font-semibold',
        //         formButtonReset:
        //             'bg-white border border-solid border-gray-200 hover:bg-transparent hover:border-black text-gray-500 hover:text-black',
        //         membersPageInviteButton:
        //             'bg-black border border-black border-solid hover:bg-white hover:text-black',
        //         card: 'bg-[#fafafa]',
        //     },
        // },
    }

    nuxtApp.vueApp.use(clerkPlugin, plugin_options)
})

function pruneUnserializableFields(authContext: AuthObject) {
    return JSON.parse(JSON.stringify(authContext))
}