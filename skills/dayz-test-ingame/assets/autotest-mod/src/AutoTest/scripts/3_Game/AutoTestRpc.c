// RPC ids of the test channel. Pick numbers no other mod uses.
const int AUTOTEST_RPC_RUN    = 74010;   // server -> client: run the client half of test <name>
const int AUTOTEST_RPC_RESULT = 74011;   // client -> server: <name>, <passed>, <message>
