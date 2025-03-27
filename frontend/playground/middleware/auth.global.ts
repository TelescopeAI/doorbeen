import { useAuth } from '@clerk/vue'

export default defineNuxtRouteMiddleware((to, from) => {
    const { isSignedIn } = useAuth()

    const publicPages = ['/auth/login', '/auth/signup']
    const isPublicPage = publicPages.includes(to.path)
    console.info("From Location: ", from.path)

    if (!isSignedIn.value && !isPublicPage) {
        return navigateTo('/auth/login')
    }  else if(isSignedIn.value && publicPages.includes(to.path)) {
        return navigateTo('/')
    }
    else if (isSignedIn.value && isPublicPage) {
        return navigateTo(from.path !== '/auth/login' ? from.path : '/')
    }
})