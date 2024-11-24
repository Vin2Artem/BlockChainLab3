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

# Интеграционный тест: регистрация через GameManager
def test_register_via_game_manager(w3, gm_contract, rps_contract, test_accounts):
    player1 = test_accounts["player1"]
    bet_amount = w3.to_wei(1, "ether")

    # Регистрация через GameManager
    tx = gm_contract.functions.registerAndTrack().build_transaction({
        "from": player1["address"],
        "value": bet_amount,
        "gas": 300000,
        "gasPrice": w3.to_wei("20", "gwei"),
        "nonce": w3.eth.get_transaction_count(player1["address"]),
    })

    signed_tx = w3.eth.account.sign_transaction(tx, private_key=player1["private_key"])
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    # Проверяем, что игрок зарегистрировался в RockPaperScissors
    player_data = rps_contract.functions.players(player1["address"]).call()
    assert player_data[2] == player1["address"]  # Проверяем, что адрес игрока совпадает

    # Проверяем, что счетчик игроков в GameManager увеличился
    player_count = gm_contract.functions.playerCount().call()
    assert player_count == 1

# Интеграционный тест: определение победителя после игры
def test_game_winner(w3, rps_contract, test_accounts):
    player1 = test_accounts["player1"]
    player2 = test_accounts["player2"]

    # Оба игрока регистрируются
    bet_amount = w3.to_wei(1, "ether")
    for player in [player1, player2]:
        tx = rps_contract.functions.register().build_transaction({
            "from": player["address"],
            "value": bet_amount,
            "gas": 300000,
            "gasPrice": w3.to_wei("20", "gwei"),
            "nonce": w3.eth.get_transaction_count(player["address"]),
        })
        signed_tx = w3.eth.account.sign_transaction(tx, private_key=player["private_key"])
        w3.eth.send_raw_transaction(signed_tx.raw_transaction)

    # Оба игрока делают commitMove
    move1, secret1 = 1, "secret123"  # Rock
    move2, secret2 = 2, "secret456"  # Paper
    commitment1 = w3.solidity_keccak(["uint8", "string"], [move1, secret1])
    commitment2 = w3.solidity_keccak(["uint8", "string"], [move2, secret2])

    for player, commitment in zip([player1, player2], [commitment1, commitment2]):
        tx = rps_contract.functions.commitMove(commitment).build_transaction({
            "from": player["address"],
            "gas": 200000,
            "gasPrice": w3.to_wei("20", "gwei"),
            "nonce": w3.eth.get_transaction_count(player["address"]),
        })
        signed_tx = w3.eth.account.sign_transaction(tx, private_key=player["private_key"])
        w3.eth.send_raw_transaction(signed_tx.raw_transaction)

    # Оба игрока раскрывают ходы
    for player, move, secret in zip([player1, player2], [move1, move2], [secret1, secret2]):
        tx = rps_contract.functions.revealMove(move, secret).build_transaction({
            "from": player["address"],
            "gas": 200000,
            "gasPrice": w3.to_wei("20", "gwei"),
            "nonce": w3.eth.get_transaction_count(player["address"]),
        })
        signed_tx = w3.eth.account.sign_transaction(tx, private_key=player["private_key"])
        w3.eth.send_raw_transaction(signed_tx.raw_transaction)

    # Проверяем, что победитель определен
    events = rps_contract.events.GameResult.createFilter(fromBlock="latest").get_all_entries()
    assert len(events) == 1
    event = events[0]
    assert event["args"]["winner"] == player2["address"]  # Player 2 должен победить (Paper > Rock)
