from ape import Contract, networks
import json

DEPLOYMENT_HEIGHT = 17583859
SNAPSHOT_HEIGHT = 23914085
MIN_BALANCE = 10**14

POOL = "0xCcd04073f4BdC4510927ea9Ba350875C3c65BF81"
YETH = "0x1BED97CBC3c24A4fb5C069C6E311a967386131f7"
WETH = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
STYETH = "0x583019fF0f430721aDa9cfb4fac8F06cA104d0B4"
CURVE_LP = "0x69ACcb968B19a53790f43e57558F5E443A91aF22"
CURVE_LP_GAUGE = "0x138cC21D15b7A06F929Fc6CFC88d2b830796F4f1"
CURVE_LP_CONVEX_REWARDS = "0xB0867ADE998641Ab1Ff04cF5cA5e5773fA92AaE3"
CURVE_LP_YEARN_STRATEGY_CONVEX = "0x472F4e5533Fb8f7fEE97DAcd3DBAE9d83867AB07"
CURVE_LP_YEARN_STRATEGY = "0x045b76468342D765bDAa6D2d74BacEE4EcDB6F5B"
CURVE_LP_YEARN_VAULT = "0x58900d761Ae3765B75DDFc235c1536B527F25d8F"
CURVE_LP_YEARN_VAULT_GAUGE = "0x81d93531720d86f0491DeE7D03f30b3b5aC24e59"
CURVE_LP_YEARN_VAULT_STAKEDAO = "0x9dB33F3CCDE2be386d6675f214dB85725FE3C714"
CURVE_LP_YEARN_VAULT_1UP = "0xCf747B983BcD8E13EE08044549b644e82D4e2d12"
CURVE_LP_YEARN_VAULT_COVE = "0x093f4FCA4b71912EDb33B2d4Bb92E5b85658D833"
CURVE_LP_STAKEDAO = "0x85496C4A63F376CA8174AC43ADAD49C5464035BD"
BOOTSTRAP = "0x7cf484D9d16BA26aB3bCdc8EC4a73aC50136d491"
POL = "0xbBBBBbbB6B942883EAd4976882C99201108c784d"
INVERSE_MARKET = "0x0c0bb843FAbda441edeFB93331cFff8EC92bD168"

YCHAD = "0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52"
YEARN_TREASURY = "0x93A62dA5a14C80f265DAbC077fCEE437B1a0Efde"
YEARN_TRADE_HANDLER = "0xb634316E06cC0B358437CbadD4dC94F1D3a92B3b"
YEARN_FEE_RECIPIENT = "0x14EFe6390C6758E3fE4379A14e3B329274b1b072"

CONVEX_PROXY = "0x989AEb4d175e16225E39E87d0D97A3360524AD80"
YEARN_CURVE_VOTER = "0xF147b8125d2ef93FB6965Db97D6746952a133934"
STAKEDAO_CURVE_VOTER = "0x52f541764E6e90eeBc5c21Ff570De0e2D63766B6"
CURVE_ROUTER = "0xF0d4c12A5768D806021F80a262B4d39d26C58b8D"

STAKEDAO_VEYFI_LOCK = "0xF750162fD81F9a436d74d737EF6eE8FC08e98220"
ONEUP_VEYFI_LOCK = "0x242521ca01f330F050a65FF5B8Ebbe92198Ae64F"
COVE_VEYFI_LOCK = "0x05dcdBF02F29239D1f8d9797E22589A2DE1C152F"

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
UNIT = 10**18
MAX = 2**256 - 1

TOKENS = [
    ["yeth", YETH],
    ["styeth", STYETH],
    ["lp", CURVE_LP],
    ["gauge", CURVE_LP_GAUGE],
    ["lp_yvault", CURVE_LP_YEARN_VAULT],
    ["lp_yvault_gauge", CURVE_LP_YEARN_VAULT_GAUGE],
    ["lp_yvault_stakedao", CURVE_LP_YEARN_VAULT_STAKEDAO],
    ["lp_yvault_1up", CURVE_LP_YEARN_VAULT_1UP],
    ["lp_yvault_cove", CURVE_LP_YEARN_VAULT_COVE],
    ["lp_stakedao", CURVE_LP_STAKEDAO],
]

def main():
    # uncomment function calls starting with `populate` to fetch the data from the chain

    # load list of contracts that are allowed to exist in the final tally (e.g. gnosis safes, 7720 delegation)
    whitelist = read_json("whitelisted_contracts")

    # build a list of addresses that interacted with the protocol in any way, using emitted events
    # of all related tokens (including LP, yVault, gauges etc), and write to a json file
    # populate_addresses()

    # build a list of Inverse escrows
    # populate_inverse_escrows()

    addresses = read_json("addresses")
    with networks.fork(provider_name="foundry", block_number=SNAPSHOT_HEIGHT) as fork:
        # build a list of balances at snapshot block using the list of addresses. includes a sanity check
        # that the balances sum up to the `totalSupply`, to make sure our list is complete
        # populate_token_balances(addresses)
        # populate_bootstrap_balances(addresses)

        # compute snapshot based on the balances
        snapshot(addresses, whitelist)

def snapshot(addresses, whitelist):
    # start with raw yETH balances
    balances = read_balances("yeth", YETH)
    yeth_supply = sum(balances.values())
    expected_sum = yeth_supply
    styeth_balances = read_balances("styeth", STYETH)
    styeth_supply = sum(styeth_balances.values())

    bootstrap = Contract(BOOTSTRAP)
    bootstrap_balances = read_json("bootstrap_balances")
    bootstrap_deposited = bootstrap.deposited()
    assert sum(bootstrap_balances.values()) == bootstrap_deposited

    # credit st-yETH to bootstrap depositors
    styeth_balances.pop(BOOTSTRAP)
    for address, balance in bootstrap_balances.items():
        styeth_balances[address] = styeth_balances.get(address, 0) + balance
    assert sum(styeth_balances.values()) == styeth_supply

    # credit st-yETH holders
    yeth_staked = balances.pop(STYETH)
    for address, balance in styeth_balances.items():
        balances[address] = balances.get(address, 0) + yeth_staked * balance // styeth_supply

    diff = expected_sum - sum(balances.values())
    assert diff >= 0 and diff <= 100 # rounding

    # credit LP holders for both the yETH and ETH
    lp_balances = calculate_lp_balances()
    lp_supply = sum(lp_balances.values())
    weth = erc20(WETH)
    lp_eth_balance = weth.balanceOf(CURVE_LP)
    expected_sum += lp_eth_balance
    lp_balance = balances.pop(CURVE_LP) + lp_eth_balance
    for address, balance in lp_balances.items():
        balances[address] = balances.get(address, 0) + lp_balance * balance // lp_supply

    # credit Inverse for all claims held inside their escrows
    inverse_escrows = read_json("inverse_escrows")
    balances["inverse"] = 0
    for address in inverse_escrows:
        balance = balances.pop(address, 0)
        if balance > 0:
            balances["inverse"] += balance

    # make sure it still adds up
    diff = expected_sum - sum(balances.values())
    assert diff >= 0 and diff <= 100 # rounding

    # zero out POL
    balances.pop(POL)

    # yearn forfeits their claims
    pop = [YCHAD, YEARN_TREASURY, YEARN_TRADE_HANDLER, YEARN_FEE_RECIPIENT]
    for p in pop:
        balances.pop(p)

    # sort by address
    sorted_balances = {}
    for address in sorted(balances.keys()):
        balance = balances[address]
        if balance >= MIN_BALANCE:
            sorted_balances[address] = balance
    balances = sorted_balances

    print(f"total claim: {sum(balances.values())/UNIT:.3f} ETH")

    write_json("snapshot", balances, dir=False)
    assert_eoas(addresses, whitelist, balances)

def calculate_lp_balances():
    # start with raw lp token balances
    lp_balances = read_balances("lp", CURVE_LP)
    lp_supply = sum(lp_balances.values())

    # credit gauge depositors
    gauge_balances = read_balances("gauge", CURVE_LP_GAUGE)
    assert lp_balances.pop(CURVE_LP_GAUGE) == sum(gauge_balances.values())
    for address, balance in gauge_balances.items():
        lp_balances[address] = lp_balances.get(address, 0) + balance

    # verify yvault strategy is the only convex depositor
    convex = erc20(CURVE_LP_CONVEX_REWARDS)
    assert convex.balanceOf(CURVE_LP_YEARN_STRATEGY_CONVEX) == lp_balances[CONVEX_PROXY]

    # credit balances of contracts related to the strategy to the yvault
    take = [CONVEX_PROXY, CURVE_LP_YEARN_STRATEGY_CONVEX, CURVE_LP_YEARN_STRATEGY, YEARN_CURVE_VOTER]
    for t in take:
        lp_balances[CURVE_LP_YEARN_VAULT] += lp_balances.pop(t)

    # credit yvault depositors
    yvault_balances = calculate_yvault_balances()
    yvault_lp_balance = lp_balances.pop(CURVE_LP_YEARN_VAULT)
    yvault_supply = sum(yvault_balances.values())
    for address, balance in yvault_balances.items():
        lp_balances[address] = lp_balances.get(address, 0) + yvault_lp_balance * balance // yvault_supply

    # credit stakedao depositors
    stakedao_balances = read_balances("lp_stakedao", CURVE_LP_STAKEDAO)
    stakedao_supply = sum(stakedao_balances.values())
    assert stakedao_supply == lp_balances.pop(STAKEDAO_CURVE_VOTER)
    for address, balance in stakedao_balances.items():
        lp_balances[address] = lp_balances.get(address, 0) + balance

    # make sure it still adds up
    diff = lp_supply - sum(lp_balances.values())
    assert diff >= 0 and diff <= 20 # rounding

    return lp_balances

def calculate_yvault_balances():
    # start with raw yvault balances
    yvault_balances = read_balances("lp_yvault", CURVE_LP_YEARN_VAULT)
    yvault_supply = sum(yvault_balances.values())

    # credit gauge depositors
    gauge_balances = read_balances("lp_yvault_gauge", CURVE_LP_YEARN_VAULT_GAUGE)
    assert yvault_balances.pop(CURVE_LP_YEARN_VAULT_GAUGE) == sum(gauge_balances.values())
    for address, balance in gauge_balances.items():
        yvault_balances[address] = yvault_balances.get(address, 0) + balance
    assert sum(yvault_balances.values()) == yvault_supply

    # credit stakedao liquid locker depositors
    stakedao_balances = read_balances("lp_yvault_stakedao", CURVE_LP_YEARN_VAULT_STAKEDAO)
    stakedao_supply = sum(stakedao_balances.values())
    assert stakedao_supply == yvault_balances.pop(STAKEDAO_VEYFI_LOCK)
    for address, balance in stakedao_balances.items():
        yvault_balances[address] = yvault_balances.get(address, 0) + balance

    # credit 1up liquid locker depositors
    oneup_balances = read_balances("lp_yvault_1up", CURVE_LP_YEARN_VAULT_1UP)
    oneup_supply = sum(oneup_balances.values())
    assert oneup_supply == yvault_balances.pop(ONEUP_VEYFI_LOCK)
    for address, balance in oneup_balances.items():
        yvault_balances[address] = yvault_balances.get(address, 0) + balance

    # credit cove liquid locker depositors
    cove_balances = read_balances("lp_yvault_cove", CURVE_LP_YEARN_VAULT_COVE)
    cove_yvault_balance = yvault_balances.pop(COVE_VEYFI_LOCK)
    cove_supply = sum(cove_balances.values())
    for address, balance in cove_balances.items():
        yvault_balances[address] = yvault_balances.get(address, 0) + cove_yvault_balance * balance // cove_supply

    # make sure it still adds up
    diff = yvault_supply - sum(yvault_balances.values())
    assert diff >= 0 and diff <= 10 # rounding

    return yvault_balances

def populate_addresses():
    print("populate addresses")
    addresses = set()
    # addresses = set(read_json("addresses").keys())

    for name, address in TOKENS:
        print(f"fetch {name} transfers")
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
    for name, token in TOKENS:
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

def populate_inverse_escrows():
    print("populate Inverse escrows")
    addresses = set()

    token = Contract(INVERSE_MARKET, abi="abi/inverse_market.json")
    events = token.CreateEscrow.query("*", start_block=DEPLOYMENT_HEIGHT, stop_block=-1)

    for ev in events["event_arguments"]:
        addresses.add(ev["escrow"])

    addresses = list(addresses)
    addresses.sort()
    write_json("inverse_escrows", addresses)

def assert_eoas(addresses, whitelist, balances):
    count = 0
    contracts = ""
    for address, balance in balances.items():
        if addresses.get(address, 0) > 0 and address not in whitelist:
            count += 1
            contracts += f"  {address}: {balance/UNIT:.5f}\n"
    if count > 0:
        print(f"Contracts:\n{contracts}")
        raise Exception(f"{count} entries are contracts")

def fetch_balances(token, addresses):
    token = erc20(token)
    balances = {}
    for address in addresses:
        balance = token.balanceOf(address)
        if balance > 0:
            balances[address] = balance
    assert sum(balances.values()) == token.totalSupply(), "not all supply accounted for"
    return balances

def read_balances(name, token):
    token = erc20(token)
    balances = read_json(f"{name}_balances")
    assert sum(balances.values()) == token.totalSupply(), "not all supply accounted for"
    return balances

def read_json(f):
    f = open(f"data/{f}.json", "r")
    r = json.load(f)
    f.close()
    return r

def write_json(f, d, dir=True):
    f = open(f"{'data/' if dir else ''}{f}.json", "w")
    json.dump(d, f, indent=2)
    f.close()

def erc20(address):
    return Contract(address, abi="abi/erc20.json")
