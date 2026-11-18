/** An HTTP-like client that retries 429 with exponential backoff (1 s, 2 s, 4 s). sleep is injectable. */
export const realSleep=ms=>new Promise(r=>setTimeout(r,ms));
export async function getWithRetry(send,{sleep=realSleep,attempts=4}={}){
  for(let i=0;i<attempts;i++){
    const res=await send();
    if(res.status!==429)return res;
    if(i<attempts-1)await sleep(1000*2**i);
  }
  return {status:429};
}
