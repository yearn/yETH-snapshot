from ape import reverts, Contract
from pytest import fixture

UNIT = 10**18
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

WETH = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
TOKEN = "0xc56413869c6CDf96496f2b1eF801fEDBdFA7dDB0" # use yvWETH-1 for testing

@fixture
def deployer(accounts):
    return accounts[0]

@fixture
def alice(accounts):
    return accounts[1]

@fixture
def bob(accounts):
    return accounts[2]

@fixture
def underlying():
    return Contract(WETH)

@fixture
def token(deployer, underlying):
    token = Contract(TOKEN)
    underlying.deposit(value=20 * UNIT, sender=deployer)
    underlying.approve(token, 20 * UNIT, sender=deployer)
    token.mint(10 * UNIT, deployer, sender=deployer)
    return token

@fixture
def claim(project, deployer, token):
    return project.Claim.deploy(token, sender=deployer)

def test_claim(chain, deployer, alice, bob, token, claim):
    # claim tokens
    claim.set_claimable([alice, bob], [2 * UNIT, UNIT], sender=deployer)
    claim.set_deadline(chain.pending_timestamp + 100, sender=deployer)
    token.transfer(claim, 3 * UNIT, sender=deployer)
    
    assert token.balanceOf(claim) == 3 * UNIT
    assert token.balanceOf(alice) == 0
    assert claim.unclaimed() == 3 * UNIT
    assert claim.claimed() == 0
    assert claim.redeemed() == 0
    assert claim.claimable(alice) == 2 * UNIT
    claim.claim(sender=alice)
    assert token.balanceOf(claim) == UNIT
    assert token.balanceOf(alice) == 2 * UNIT
    assert claim.unclaimed() == UNIT
    assert claim.claimed() == 2 * UNIT
    assert claim.redeemed() == 0
    assert claim.claimable(alice) == 0

    assert token.balanceOf(bob) == 0
    assert claim.claimable(bob) == UNIT
    claim.claim(sender=bob)
    assert token.balanceOf(claim) == 0
    assert token.balanceOf(bob) == UNIT
    assert claim.claimed() == 3 * UNIT
    assert claim.claimable(bob) == 0

def test_claim_redeem(chain, deployer, alice, bob, underlying, token, claim):
    # redeem for underlying during claim
    claim.set_claimable([alice, bob], [2 * UNIT, UNIT], sender=deployer)
    claim.set_deadline(chain.pending_timestamp + 100, sender=deployer)
    token.transfer(claim, 3 * UNIT, sender=deployer)
    
    claim.claim(True, sender=alice)
    assert token.balanceOf(claim) == UNIT
    assert token.balanceOf(alice) == 0
    assert abs(underlying.balanceOf(alice) - token.convertToAssets(2 * UNIT)) <= 1
    assert claim.unclaimed() == UNIT
    assert claim.claimed() == 2 * UNIT
    assert claim.redeemed() == 2 * UNIT
    assert claim.claimable(alice) == 0

    claim.claim(True, sender=bob)
    assert token.balanceOf(claim) == 0
    assert token.balanceOf(bob) == 0
    assert abs(underlying.balanceOf(bob) - token.convertToAssets(UNIT)) <= 1
    assert claim.unclaimed() == 0
    assert claim.claimed() == 3 * UNIT
    assert claim.redeemed() == 3 * UNIT
    assert claim.claimable(bob) == 0

def test_claim_double(chain, deployer, alice, token, claim):
    # cant claim more than once
    claim.set_claimable([alice], [UNIT], sender=deployer)
    claim.set_deadline(chain.pending_timestamp + 100, sender=deployer)
    token.transfer(claim, UNIT, sender=deployer)

    claim.claim(sender=alice)
    with reverts():
        claim.claim(sender=alice)

def test_claim_invalid(chain, deployer, alice, bob, token, claim):
    # cant claim without a claimable amount
    claim.set_claimable([alice], [UNIT], sender=deployer)
    claim.set_deadline(chain.pending_timestamp + 100, sender=deployer)
    token.transfer(claim, UNIT, sender=deployer)

    with reverts():
        claim.claim(sender=bob)
    claim.claim(sender=alice)

def test_claim_deadline(chain, deployer, alice, bob, token, claim):
    # cant claim without a claimable amount
    claim.set_claimable([alice], [UNIT], sender=deployer)
    deadline = chain.pending_timestamp + 100
    claim.set_deadline(deadline, sender=deployer)
    token.transfer(claim, UNIT, sender=deployer)

    chain.pending_timestamp = deadline
    with reverts():
        claim.claim(sender=bob)

    claim.set_deadline(deadline + 100, sender=deployer)
    claim.claim(sender=alice)

def test_sweep(deployer, token, claim):
    # tokens can be transferred out
    token.transfer(claim, 10 * UNIT, sender=deployer)
    assert token.balanceOf(claim) == 10 * UNIT
    assert token.balanceOf(deployer) == 0
    claim.sweep(token, sender=deployer)
    assert token.balanceOf(claim) == 0
    assert token.balanceOf(deployer) == 10 * UNIT

def test_sweep_permission(deployer, alice, token, claim):
    # only management can transfer tokens out
    token.transfer(claim, UNIT, sender=deployer)
    with reverts():
        claim.sweep(token, sender=alice)
    claim.sweep(token, sender=deployer)

def test_set_claimable(deployer, alice, bob, claim):
    # claimable amounts can be set
    assert claim.unclaimed() == 0
    assert claim.claimable(alice) == 0
    assert claim.claimable(bob) == 0
    claim.set_claimable([alice, bob], [2 * UNIT, UNIT], sender=deployer)
    assert claim.unclaimed() == 3 * UNIT
    assert claim.claimable(alice) == 2 * UNIT
    assert claim.claimable(bob) == UNIT

    # increase amount
    claim.set_claimable([bob], [4 * UNIT], sender=deployer)
    assert claim.unclaimed() == 6 * UNIT
    assert claim.claimable(bob) == 4 * UNIT

    # decrease amount
    claim.set_claimable([bob], [3 * UNIT], sender=deployer)
    assert claim.unclaimed() == 5 * UNIT
    assert claim.claimable(bob) == 3 * UNIT

def test_set_claimable_permission(deployer, alice, claim):
    # only management can set claimable amounts
    with reverts():
        claim.set_claimable([alice], [UNIT], sender=alice)
    claim.set_claimable([alice], [UNIT], sender=deployer)

def test_set_deadline_permission(chain, deployer, alice, claim):
    # deadline can be set
    deadline = chain.pending_timestamp + 100
    with reverts():
            claim.set_deadline(deadline, sender=alice)
    claim.set_deadline(deadline, sender=deployer)

def test_set_deadline(chain, deployer, claim):
    # deadline can be set
    deadline = chain.pending_timestamp + 100
    assert claim.deadline() == 0
    claim.set_deadline(deadline, sender=deployer)
    assert claim.deadline() == deadline

def test_set_deadline_permission(chain, deployer, alice, claim):
    # deadline can be set
    deadline = chain.pending_timestamp + 100
    with reverts():
            claim.set_deadline(deadline, sender=alice)
    claim.set_deadline(deadline, sender=deployer)

def test_set_management(deployer, alice, claim):
    # management can propose a replacement
    assert claim.management() == deployer
    assert claim.pending_management() == ZERO_ADDRESS
    claim.set_management(alice, sender=deployer)
    assert claim.management() == deployer
    assert claim.pending_management() == alice

def test_set_management_undo(deployer, alice, claim):
    # proposed replacement can be undone
    claim.set_management(alice, sender=deployer)
    claim.set_management(ZERO_ADDRESS, sender=deployer)
    assert claim.management() == deployer
    assert claim.pending_management() == ZERO_ADDRESS

def test_set_management_permission(alice, claim):
    # only management can propose a replacement
    with reverts():
        claim.set_management(alice, sender=alice)

def test_accept_management(deployer, alice, claim):
    # replacement can accept management role
    claim.set_management(alice, sender=deployer)
    claim.accept_management(sender=alice)
    assert claim.management() == alice
    assert claim.pending_management() == ZERO_ADDRESS

def test_accept_management_early(alice, claim):
    # cant accept management role without being nominated
    with reverts():
        claim.accept_management(sender=alice)

def test_accept_management_wrong(deployer, alice, bob, claim):
    # cant accept management role without being the nominee
    claim.set_management(alice, sender=deployer)
    with reverts():
        claim.accept_management(sender=bob)
