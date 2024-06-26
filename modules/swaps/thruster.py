import time

from modules import DEX, Logger, RequestClient
from utils.tools import helper
from general_settings import SLIPPAGE
from hexbytes import HexBytes
from config import (
    THRUSTER_ABI,
    THRUSTER_CONTRACTS,
    TOKENS_PER_CHAIN
)


class Thruster(DEX, Logger, RequestClient):
    def __init__(self, client):
        self.client = client
        Logger.__init__(self)
        self.network = self.client.network.name
        self.router_contract = self.client.get_contract(
            THRUSTER_CONTRACTS[self.network]['router'],
            THRUSTER_ABI['router'])

    @staticmethod
    def get_path(from_token_address: str, to_token_address: str):
        from_token_bytes = HexBytes(from_token_address).rjust(20, b'\0')
        to_token_bytes = HexBytes(to_token_address).rjust(20, b'\0')
        fee_bytes = (500).to_bytes(3, 'big')

        return from_token_bytes + fee_bytes + to_token_bytes

    async def get_min_amount_out(self, amount_in_wei, token_in, token_out):
        url = f"https://thruster-api-fmzkxtajbq-uc.a.run.app/quote"

        headers = {
            "accept": "*/*",
            "accept-language": "ru,en;q=0.9,en-GB;q=0.8,en-US;q=0.7",
            "sec-ch-ua": "\"Chromium\";v=\"122\", \"Not(A:Brand\";v=\"24\", \"Microsoft Edge\";v=\"122\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "cross-site",
            "referrer": "https://app.thruster.finance/",
            "referrerPolicy": "strict-origin-when-cross-origin",
            "method": "GET",
            "mode": "cors",
            "credentials": "omit"
        }

        params = {
         'amount': amount_in_wei,
         'tokenIn': token_in.lower(),
         'tokenOut': token_out.lower(),
         'type': 'EXACT_INPUT',
         'chainId': self.client.chain_id
        }

        response = await self.make_request(method="GET", url=url, params=params, headers=headers)
        min_amount_out = int(response['bestQuote']['quote'].split('.')[0])
        return int(min_amount_out - (min_amount_out / 100 * SLIPPAGE))

    @helper
    async def swap(self, swapdata: tuple = None):
        if not swapdata:
            from_token_name, to_token_name, amount, amount_in_wei = await self.client.get_auto_amount()
        else:
            from_token_name, to_token_name, amount, amount_in_wei = swapdata

        self.logger_msg(
            *self.client.acc_info, msg=f'Swap on Thruster: {amount} {from_token_name} -> {to_token_name}')

        from_token_address = TOKENS_PER_CHAIN[self.network][from_token_name]
        to_token_address = TOKENS_PER_CHAIN[self.network][to_token_name]
        deadline = int(time.time()) + 1000000
        path = self.get_path(from_token_address, to_token_address)
        min_amount_out = await self.get_min_amount_out(amount_in_wei, from_token_address, to_token_address)

        if from_token_name != 'ETH':
            await self.client.check_for_approved(
                from_token_address, THRUSTER_CONTRACTS[self.network]['router'], amount_in_wei
            )

        tx_data = self.router_contract.encodeABI(
            fn_name='exactInput',
            args=[(
                path,
                self.client.address if to_token_name != 'ETH' else '0x0000000000000000000000000000000000000002',
                deadline,
                amount_in_wei,
                min_amount_out
            )]
        )

        full_data = [tx_data]

        if from_token_name == 'ETH' or to_token_name == 'ETH':
            tx_additional_data = self.router_contract.encodeABI(
                fn_name='unwrapWETH9' if from_token_name != 'ETH' else 'refundETH',
                args=[
                    min_amount_out,
                    self.client.address
                ] if from_token_name != 'ETH' else None
            )
            full_data.append(tx_additional_data)
        print(full_data)
        tx_params = await self.client.prepare_transaction(value=amount_in_wei if from_token_name == 'ETH' else 0)
        transaction = await self.router_contract.functions.multicall(
            full_data
        ).build_transaction(tx_params)
        print(transaction)
        return
        return await self.client.send_transaction(transaction)
