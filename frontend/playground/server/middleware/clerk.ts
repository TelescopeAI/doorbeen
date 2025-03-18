import { clerkMiddleware } from 'h3-clerk'

const publishableKey  = useRuntimeConfig().public.clerkPublicKey
const domain  = useRuntimeConfig().public.clerkDomain

export default clerkMiddleware({publishableKey: publishableKey, domain: domain})