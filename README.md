Run data-retrieval/getmutuals.py with your Discord user token. This creates a json file called mutuals_output that contains the relational data from the Discord relationships endpoint. Note that due to limitations with the API,
this includes your friends **as well as people you have blocked, sent a friend request to, or recieved a friend request from**.
run buildgraph.py to generate graph.html. 

You may put graph.html in a directory on the root of this project named "public" to host it using the included dockercompose and env examples with an authenticator app gating access! 

Alternatively, simply open/host graph.html directly to view your relations graphed! 

WIP: Ability to update the mutuals_output json without reiterating through all relationships again

Disclaimer: everything except for getmutuals.py was very much vibe coded, use at your own risk. 

getmutuals.py should also be used at your own risk as it is against Discord TOS to automate requests like this using your token and this falls under selfbotting (if the playwright browser to bypass Cloudflare JS challenges wasn't obvious enough), I was able to get my relations list of ~750 people without issue, but your mileage may vary. 
