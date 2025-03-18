

export const getAPIServerURL = (stream: boolean = false) => {
    const server_url = useRuntimeConfig().public.apiServerURL
    const is_production = useRuntimeConfig().public.environment === "production"
    let protocol = stream ? "ws" : "http"
    let url = null
    // if(is_production){
    //     protocol += "s"
    // }
    url = `${protocol}://${server_url}`
    console.log("API Server URL: ", url)
    return url

}

