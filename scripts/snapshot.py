from ape import Contract, networks, accounts
import json

DEPLOYMENT_HEIGHT = 17583859
SNAPSHOT_HEIGHT = 23914085

POOL = "0xCcd04073f4BdC4510927ea9Ba350875C3c65BF81"
YETH = "0x1BED97CBC3c24A4fb5C069C6E311a967386131f7"
WETH = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
STYETH = "0x583019fF0f430721aDa9cfb4fac8F06cA104d0B4"
CURVE_LP = "0x69ACcb968B19a53790f43e57558F5E443A91aF22"
CURVE_LP_GAUGE = "0x138cC21D15b7A06F929Fc6CFC88d2b830796F4f1"
CURVE_LP_CONVEX_REWARDS = "0xB0867ADE998641Ab1Ff04cF5cA5e5773fA92AaE3"
CURVE_LP_YEARN = "0x472F4e5533Fb8f7fEE97DAcd3DBAE9d83867AB07"
BOOTSTRAP = "0x7cf484D9d16BA26aB3bCdc8EC4a73aC50136d491"
CONVEX_PROXY = "0x989AEb4d175e16225E39E87d0D97A3360524AD80"

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
UNIT = 10**18
MAX = 2**256 - 1

NAMES = ["yeth", "styeth", "lp", "gauge"]
TOKENS = [YETH, STYETH, CURVE_LP, CURVE_LP_GAUGE]

def main():
    # comment out function calls starting with `populate` to only read from disk

    # build a list of addresses that interacted with the protocol using emitted events
    populate_addresses()
    addresses = read_json("addresses")

    with networks.fork(provider_name="foundry", block_number=SNAPSHOT_HEIGHT) as fork:
        populate_token_balances(addresses)
        populate_bootstrap_balances(addresses)
        snapshot(addresses)

def snapshot(addresses):
    # balances = read_balances("yeth", YETH)
    # yeth_supply = sum(balances.values())
    # styeth_balances = read_balances("styeth", STYETH)
    # styeth_supply = sum(styeth_balances.values())

    # bootstrap = Contract(BOOTSTRAP)
    # bootstrap_balances = read_json("bootstrap_balances")
    # bootstrap_deposited = bootstrap.deposited()
    # assert sum(bootstrap_balances.values()) == bootstrap_deposited

    # # credit st-yETH to bootstrap depositors
    # styeth_balances.pop(BOOTSTRAP)
    # for address, balance in bootstrap_balances.items():
    #     if address not in styeth_balances:
    #         styeth_balances[address] = 0
    #     styeth_balances[address] += balance
    # assert sum(styeth_balances.values()) == styeth_supply

    # # credit yETH to st-yETH holders
    # yeth_staked = balances.pop(STYETH)
    # for address, balance in styeth_balances.items():
    #     if address not in balances:
    #         balances[address] = 0
    #     balances[address] += yeth_staked * balance // styeth_supply
    # diff = yeth_supply - sum(balances.values())
    # assert diff >= 0 and diff <= 100 # rounding

    lp_balances = calculate_lp_balances(addresses)
    for address, balance in lp_balances.items():
        print(f"{address}: {balance/UNIT:.3f}")

def calculate_lp_balances(addresses):
    # naked LP token
    lp_balances = read_balances("lp", CURVE_LP)
    lp_supply = sum(lp_balances.values())

    # gauge
    gauge_balances = read_balances("gauge", CURVE_LP_GAUGE)
    assert lp_balances.pop(CURVE_LP_GAUGE) == sum(gauge_balances.values())
    for address, balance in gauge_balances.items():
        lp_balances[address] = lp_balances.get(address, 0) + balance

    # yearn strategy is the only convex depositor
    convex_balance = lp_balances.pop(CONVEX_PROXY)
    convex = erc20(CURVE_LP_CONVEX_REWARDS)
    assert convex.balanceOf(CURVE_LP_YEARN) == convex_balance

    assert sum(lp_balances.values()) == lp_supply

    assert_eoas(addresses, lp_balances)
    return lp_balances

def populate_addresses():
    print("populate addresses")
    addresses = set()

    for address in TOKENS:
        token = erc20(address)
        events = token.Transfer.query("*", start_block=DEPLOYMENT_HEIGHT, stop_block=-1)

        for ev in events["event_arguments"]:
            addresses.add(ev["sender"])
            addresses.add(ev["receiver"])

    bootstrap = Contract(BOOTSTRAP)
    events = bootstrap.Deposit.query("*", start_block=DEPLOYMENT_HEIGHT, stop_block=-1)
    for ev in events["event_arguments"]:
        addresses.add(ev["receiver"])

    addresses.discard(ZERO_ADDRESS)
    addresses = list(addresses)
    addresses.sort()

    sizes = {}
    for address in addresses:
        size = len(networks.provider.get_code(address))
        sizes[address] = size

    write_json("addresses", sizes)

def populate_token_balances(addresses):
    for name, token in zip(NAMES, TOKENS):
        print(f"populate {name} balances")
        balances = fetch_balances(token, addresses)
        write_json(f"{name}_balances", balances)

def populate_bootstrap_balances(addresses):
    print("populate bootstrap balances")
    bootstrap = Contract(BOOTSTRAP)
    balances = {}
    for address in addresses:
        balance = bootstrap.deposits(address)
        if balance > 0:
            balances[address] = balance
    assert sum(balances.values()) == bootstrap.deposited()
    write_json("bootstrap_balances", balances)

def assert_eoas(addresses, balances):
    contracts = set()
    for address in balances.keys():
        if addresses[address] > 0:
            contracts.add(address)
    if len(contracts) > 0:
        print("Contracts:")
        for contract in contracts:
            print(f"  {contract}")
        raise Exception(f"{len(contracts)} entries are contracts")

def fetch_balances(token, addresses):
    token = erc20(token)
    balances = {}
    for address in addresses:
        balance = token.balanceOf(address)
        if balance > 0:
            balances[address] = balance
    assert sum(balances.values()) == token.totalSupply()
    return balances

def read_balances(name, token):
    token = erc20(token)
    balances = read_json(f"{name}_balances")
    assert sum(balances.values()) == token.totalSupply()
    return balances

def read_json(f):
    f = open(f"data/{f}.json", "r")
    r = json.load(f)
    f.close()
    return r

def write_json(f, d):
    f = open(f"data/{f}.json", "w")
    json.dump(d, f, indent=2)
    f.close()

def erc20(address):
    return Contract(address, abi="abi/erc20.json")
