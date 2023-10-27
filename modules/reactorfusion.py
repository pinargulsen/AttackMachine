from utils.tools import gas_checker, repeater
from config import REACTORFUSION_CONTRACTS, REACTORFUSION_ABI
from modules import Client


class ReactorFusion(Client):
    def __init__(self, account_number, private_key, network, proxy=None):
        super().__init__(account_number, private_key, network, proxy)
        self.landing_contract = self.get_contract(REACTORFUSION_CONTRACTS['landing'], REACTORFUSION_ABI)
        self.collateral_contract = self.get_contract(REACTORFUSION_CONTRACTS['collateral'], REACTORFUSION_ABI)

    @repeater
    @gas_checker
    async def deposit(self):

        amount, amount_in_wei = await self.check_and_get_eth_for_deposit()

        self.logger.info(f'{self.info} Deposit to ReactorFusion: {amount} ETH')

        tx_params = await (self.prepare_transaction()) | {
            'to': REACTORFUSION_CONTRACTS['landing'],
            'value': amount_in_wei,
            'data': '0x1249c58b'
        }

        tx_hash = await self.send_transaction(tx_params)

        await self.verify_transaction(tx_hash)

    @repeater
    @gas_checker
    async def withdraw(self):
        self.logger.info(f'{self.info} Withdraw from ReactorFusion')

        liquidity_balance = await self.landing_contract.functions.balanceOf(self.address).call()

        if liquidity_balance != 0:

            tx_params = await self.prepare_transaction()

            transaction = await self.landing_contract.functions.redeem(
                liquidity_balance
            ).build_transaction(tx_params)

            tx_hash = await self.send_transaction(transaction)

            await self.verify_transaction(tx_hash)

        else:
            self.logger.error(f'{self.info} Insufficient balance on ReactorFusion!')

    @repeater
    @gas_checker
    async def enable_collateral(self):
        self.logger.info(f'{self.info} Enable collateral on ReactorFusion')

        tx_params = await self.prepare_transaction()

        transaction = await self.collateral_contract.functions.enterMarkets(
            [REACTORFUSION_CONTRACTS['landing']]
        ).build_transaction(tx_params)

        tx_hash = await self.send_transaction(transaction)

        await self.verify_transaction(tx_hash)

    @repeater
    @gas_checker
    async def disable_collateral(self):
        self.logger.info(f'{self.info} Disable collateral on ReactorFusion')

        tx_params = await self.prepare_transaction()

        transaction = await self.collateral_contract.functions.exitMarket(
            REACTORFUSION_CONTRACTS['landing']
        ).build_transaction(tx_params)

        tx_hash = await self.send_transaction(transaction)

        await self.verify_transaction(tx_hash)