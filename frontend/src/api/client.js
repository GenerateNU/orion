//This file is so that we don't reuse fetch for every hook/endpoint. 

// Allows us to use this function elsewhere 
export async function apiClient(endpoint) {
    const response = await fetch(endpoint);
  
// error handling 
    if (!response.ok) {
      throw new Error(`API request failed: ${response.status}`);
    }
  
    return response.json();
  }