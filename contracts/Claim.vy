# pragma version 0.4.2
# pragma optimize gas
# pragma evm-version cancun
"""
@title yETH recovery claim
@author Yearn Finance
@license GNU AGPLv3
@notice Allows a set of pre-configured addresses to claim their vault tokens up until a deadline.
        Users can optionally redeem the vault token for the underlying token during their claim.
"""

from ethereum.ercs import IERC20
from ethereum.ercs import IERC4626

token: public(immutable(address))
management: public(address)
pending_management: public(address)
unclaimed: public(uint256)
claimed: public(uint256)
redeemed: public(uint256)
deadline: public(uint256)
claimable: public(HashMap[address, uint256])

event Claim:
    account: indexed(address)
    amount: uint256
    redeem: bool

event SetClaim:
    account: indexed(address)
    amount: uint256

event SetDeadline:
    deadline: uint256

event PendingManagement:
    management: indexed(address)

event SetManagement:
    management: indexed(address)

@deploy
def __init__(_token: address):
    """
    @notice Constructor
    @param _token Vault token address
    """
    token = _token
    self.management = msg.sender

@external
def claim(_redeem: bool = False):
    """
    @notice Claim vault tokens and optionally redeem for underlying
    @param _redeem False: claim vault tokens, True: claim and redeem for underlying
    """
    assert block.timestamp < self.deadline
    amount: uint256 = self.claimable[msg.sender]
    assert amount > 0

    self.claimable[msg.sender] = 0
    self.unclaimed -= amount
    self.claimed += amount

    if _redeem:
        self.redeemed += amount
        extcall IERC4626(token).redeem(amount, msg.sender, self)
    else:
        assert extcall IERC20(token).transfer(msg.sender, amount, default_return_value=True)

    log Claim(account=msg.sender, amount=amount, redeem=_redeem)

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
    @param _amounts List of claimable amounts corresponding to each account
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
