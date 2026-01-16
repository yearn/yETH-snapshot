# yETH snapshot
Python script used to generate the [yETH snapshot](./snapshot.json) at block 23914085. Final snapshot is denominated in ETH and is filtered with a minimum value of 0.0001 ETH.

The script starts out with the raw yETH balances and recursively replaces balances of contracts with their underlying depositors across all protocols (st-yETH, Curve, Convex, Yearn vaults, Yearn dYFI gauge, StakeDAO, 1UP, Cove, Inverse, Balancer, Aura) until there are no contracts left, outside of a list of whitelisted contracts such as Safe multisigs and 7702 delegations.

## Usage

### Install dependencies
```sh
# Install foundry
curl -L https://foundry.paradigm.xyz | bash
foundryup
# Install ape
pip install eth-ape
# Install required ape plugins
ape plugins install .
```
Inside `~/.ape/ape-config.yaml`, set a default node for Ethereum mainnet.

### Run
In order to generate the snapshot, execute
```sh
ape run snapshot
```

This uses prefetched lists of token balances in order to speed up calculations. These lists can be generated from scratch by uncommenting function calls of functions starting with `populate` inside the `main` function of [`snapshot.py`](./scripts/snapshot.py).
