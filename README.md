Run data-retrieval/getmutuals.py with your Discord user token. This creates a json file called mutuals_output that contains the relational data from the Discord relationships endpoint. Note that due to limitations with the API,
this includes your friends **as well as people you have blocked, sent a friend request to, or recieved a friend request from**.
run buildgraph.py to generate graph.html. 

You may put graph.html in a directory on the root of this project named "public" to host it using the included dockercompose and env examples with an authenticator app gating access! 

Alternatively, simply open/host graph.html directly to view your relations graphed! 

WIP: Ability to update the mutuals_output json without reiterating through all relationships again
