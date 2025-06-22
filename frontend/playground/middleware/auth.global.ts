import { useAuth } from '@clerk/vue'

export default defineNuxtRouteMiddleware((to, from) => {
    const { isSignedIn, isLoaded } = useAuth()

    const publicPages = ['/auth/login', '/auth/signup']
    const isPublicPage = publicPages.includes(to.path)
    const isChatRoute = to.path.startsWith('/chat/')
    
    console.info("From Location: ", from.path)
    console.info("To Location: ", to.path)
    console.info("Is Chat Route: ", isChatRoute)
    console.info("Is Signed In: ", isSignedIn.value)
    console.info("Is Loaded: ", isLoaded.value)

    // If auth is still loading, don't redirect yet
    if (!isLoaded.value) {
        console.info("Auth still loading, allowing navigation to proceed")
        return
    }

    // If user is not signed in and trying to access a protected page
    if (!isSignedIn.value && !isPublicPage) {
        console.info("User not signed in, redirecting to login")
        return navigateTo('/auth/login')
    }
    
    // If user is signed in and trying to access auth pages, redirect appropriately
    if (isSignedIn.value && isPublicPage) {
        console.info("User signed in but trying to access auth page, redirecting")
        // If coming from a chat route, go back to that chat route
        if (from.path.startsWith('/chat/')) {
            return navigateTo(from.path)
        }
        // Otherwise go to home
        return navigateTo('/')
    }
    
    console.info("Allowing navigation to proceed")
    // Allow all other navigation for signed-in users (including chat routes)
})