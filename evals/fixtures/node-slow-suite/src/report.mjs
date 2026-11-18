/** Events in the window [from, to); the default window is the last 30 days up to now. */
export function eventsInWindow(events,{from,to}={}){
  const now=Date.now(),start=from??now-30*86400e3,end=to??now+1;
  return events.filter(e=>e.at>=start&&e.at<end);
}
