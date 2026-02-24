# pragma version 0.4.2
# pragma optimize gas
# pragma evm-version cancun
"""
@title yETH recovery claim
@author Yearn Finance
@license GNU AGPLv3
@notice Allows a set of pre-configured addresses to claim their recovery vault tokens up until a deadline.
        Users can optionally exit during the claim and receive the recovered underlying token instead,
        opting out of the recovery program permanently.
"""

from ethereum.ercs import IERC20
from ethereum.ercs import IERC4626

yield_vault: public(immutable(IERC4626))
recovery_vault: public(immutable(IERC4626))
recovery_rate: public(immutable(uint256))

management: public(address)
pending_management: public(address)
unclaimed: public(uint256)
claimed: public(uint256)
exited: public(uint256)
deadline: public(uint256)
claimable: public(HashMap[address, uint256])

event Claim:
    account: indexed(address)
    amount: uint256
    underlying: uint256
    shares: uint256

event SetClaim:
    account: indexed(address)
    amount: uint256

event SetDeadline:
    deadline: uint256

event PendingManagement:
    management: indexed(address)

event SetManagement:
    management: indexed(address)

PRECISION: constant(uint256) = 10**18

@deploy
def __init__(_yield_vault: address, _recovery_vault: address, _recovery_rate: uint256):
    """
    @notice Constructor
    @param _yield_vault Yield vault address
    @param _recovery_vault Recovery vault address
    @param _recovery_rate Recovery rate (18 decimals)
    """
    assert _recovery_rate < PRECISION
    
    yield_vault = IERC4626(_yield_vault)
    recovery_vault = IERC4626(_recovery_vault)
    recovery_rate = _recovery_rate
    self.management = msg.sender

    underlying: address = staticcall recovery_vault.asset()
    assert staticcall yield_vault.asset() == underlying
    extcall IERC20(underlying).approve(_recovery_vault, max_value(uint256))

@external
def claim(_exit: bool = False) -> (uint256, uint256):
    """
    @notice Claim tokens and optionally receive the underlying token
    @param _exit False: receive recovery token, True: receive underlying token
    @return Tuple with amount after applying recovery rate and minted shares of recovery vault
    """
    assert block.timestamp < self.deadline
    amount: uint256 = self.claimable[msg.sender]
    assert amount > 0

    self.claimable[msg.sender] = 0
    self.unclaimed -= amount
    self.claimed += amount

    underlying: uint256 = amount * recovery_rate // PRECISION
    shares: uint256 = 0
    if _exit:
        self.exited += amount
        extcall yield_vault.withdraw(underlying, msg.sender, self)
    else:
        extcall yield_vault.withdraw(underlying, self, self)
        shares = extcall recovery_vault.deposit(underlying, msg.sender)

    log Claim(account=msg.sender, amount=amount, underlying=underlying, shares=shares)
    return underlying, shares

@external
def sweep(_token: address, _amount: uint256 = max_value(uint256)):
    """
    @notice Transfer out a token
    @param _token The token address
    @param _amount The amount of tokens. Defaults to all
    @dev Can only be called by management
    """
    assert msg.sender == self.management

    amount: uint256 = _amount
    if _amount == max_value(uint256):
        amount = staticcall IERC20(_token).balanceOf(self)

    assert extcall IERC20(_token).transfer(msg.sender, amount, default_return_value=True)

@external
def set_claimable(_accounts: DynArray[address, 64], _amounts: DynArray[uint256, 64]):
    """
    @notice Set the claimable amount for a set of addresses
    @param _accounts List of account
    @param _amounts Corresponding list of claimable amounts (before applying recovery rate)
    @dev Can only be called by management
    """
    assert msg.sender == self.management
    assert len(_accounts) == len(_amounts)

    unclaimed: uint256 = self.unclaimed
    for i: uint256 in range(len(_accounts), bound=64):
        account: address = _accounts[i]
        amount: uint256 = _amounts[i]
        unclaimed = unclaimed - self.claimable[account] + amount
        self.claimable[account] = amount
        log SetClaim(account=account, amount=amount)
    self.unclaimed = unclaimed

@external
def set_deadline(_deadline: uint256):
    """
    @notice Set the timestamp after which claims are no longer allowed
    @param _deadline Claim deadline
    @dev Can only be called by management
    """
    assert msg.sender == self.management

    self.deadline = _deadline
    log SetDeadline(deadline=_deadline)

@external
def set_management(_management: address):
    """
    @notice Set the pending management address.
            Needs to be accepted by that account separately to transfer management over
    @param _management New pending management address
    """
    assert msg.sender == self.management

    self.pending_management = _management
    log PendingManagement(management=_management)

@external
def accept_management():
    """
    @notice Accept management role.
            Can only be called by account previously marked as pending by current management
    """
    assert msg.sender == self.pending_management

    self.pending_management = empty(address)
    self.management = msg.sender
    log SetManagement(management=msg.sender)
