import {getAPIServerURL} from "~/composables/server";

export const get_sample_data = async () => {
    const url = getAPIServerURL() + "/api/v1/sandbox/databases";
    // Adjust the request as necessary, possibly including connection details
    const { data, error } = await useFetch(url, {
        key: url,
        method: "GET",
    });
    if (error.value) {
        console.log("Error: ", error.value);
    }
    return data.value
};