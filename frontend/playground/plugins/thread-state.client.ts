export default defineNuxtPlugin(async () => {
  // Initialize current thread from localStorage on client side
  const { initializeFromStorage } = useCurrentThread()
 
  // Initialize from localStorage if available
  await initializeFromStorage()
}) 