import pytest
from web3 import Web3
import json


def get_updated_gas_price(w3):
    """
    Получает обновленную цену газа на основе состояния сети.

    :param w3: объект Web3
    :return: обновленная цена газа в wei
    """
    try:
        # Получаем текущую базовую цену газа
        current_gas_price = w3.eth.gas_price
        
        # Увеличиваем базовую цену газа на 20%
        adjusted_gas_price = int(current_gas_price * 1.2)
        print(f"Текущая цена газа: {current_gas_price} wei, Увеличенная цена: {adjusted_gas_price} wei")
        
        return adjusted_gas_price
    except Exception as e:
        print(f"Ошибка при обновлении цены газа: {e}")
        return w3.toWei('20', 'gwei')  # Возвращаем дефолтное значение, если произошла ошибка

# Подключение к тестовой сети
@pytest.fixture
def w3():
    provider_url = "https://sepolia.infura.io/v3/api"
    return Web3(Web3.HTTPProvider(provider_url))

# Загрузка ABI контрактов
@pytest.fixture
def rps_contract(w3):
    rps_address = "0x1F61A9e28bb452e4284acF44520C79F14610711f"
    with open("RockPaperScissors.json") as f:
        rps_abi = json.load(f)
    return w3.eth.contract(address=rps_address, abi=rps_abi)

@pytest.fixture
def gm_contract(w3):
    gm_address = "0x520878D21A36bD3BAEED9eAA93cA825bF32a2284"
    with open("GameManager.json") as f:
        gm_abi = json.load(f)
    return w3.eth.contract(address=gm_address, abi=gm_abi)

# Приватные ключи и адреса тестовых аккаунтов
@pytest.fixture
def test_accounts():
    return {
        "player1": {
            "private_key": "private_key1",
            "address": "address1",
        },
        "player2": {
            "private_key": "private_key2",
            "address": "address2",
        },
    }

# Тест регистрации игрока
def test_register_player(w3, rps_contract, test_accounts):
    player1 = test_accounts["player1"]
    bet_amount = w3.to_wei(1, "ether")
    updated_gas_price = get_updated_gas_price(w3)
    print("updated_gas =", updated_gas_price)
    updated_gas_price = int(updated_gas_price * 2)
    print("updated_gas1 =", updated_gas_price)

    # Формируем транзакцию
    tx = rps_contract.functions.register().build_transaction({
        "from": player1["address"],
        "value": bet_amount,
        "gas": 300000,
        "gasPrice": w3.to_wei("20", "gwei"),
        "nonce": w3.eth.get_transaction_count(player1["address"]),
    })

    # Подписываем и отправляем транзакцию
    signed_tx = w3.eth.account.sign_transaction(tx, private_key=player1["private_key"])
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    # Проверяем, что игрок зарегистрирован
    player_data = rps_contract.functions.players(player1["address"]).call()
    assert player_data[2] == player1["address"]  # Адрес игрока

# Тест вызова commitMove
def test_commit_move(w3, rps_contract, test_accounts):
    player1 = test_accounts["player1"]

    move = 1  # Rock
    secret = "secret123"
    commitment = w3.solidity_keccak(["uint8", "string"], [move, secret])

    # Формируем транзакцию
    tx = rps_contract.functions.commitMove(commitment).build_transaction({
        "from": player1["address"],
        "gas": 200000,
        "gasPrice": w3.to_wei("20", "gwei"),
        "nonce": w3.eth.get_transaction_count(player1["address"]),
    })

    # Подписываем и отправляем транзакцию
    signed_tx = w3.eth.account.sign_transaction(tx, private_key=player1["private_key"])
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    # Проверяем, что коммит зарегистрирован
    player_data = rps_contract.functions.players(player1["address"]).call()
    assert player_data[0] == commitment  # Хэш-коммит игрока

# Тест вызова revealMove
def test_reveal_move(w3, rps_contract, test_accounts):
    player1 = test_accounts["player1"]

    move = 1  # Rock
    secret = "secret123"

    # Формируем транзакцию
    tx = rps_contract.functions.revealMove(move, secret).build_transaction({
        "from": player1["address"],
        "gas": 200000,
        "gasPrice": w3.to_wei("20", "gwei"),
        "nonce": w3.eth.get_transaction_count(player1["address"]),
    })

    # Подписываем и отправляем транзакцию
    signed_tx = w3.eth.account.sign_transaction(tx, private_key=player1["private_key"])
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    # Проверяем, что игрок раскрыл ход
    player_data = rps_contract.functions.players(player1["address"]).call()
    assert player_data[1] == move  # Ход игрока