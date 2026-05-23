import requests

USERS_API_URL = "https://jsonplaceholder.typicode.com/users"


def fetch_users(url: str) -> list[dict]:
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


def print_user_names_and_emails(users: list[dict]) -> None:
    for user in users:
        name = user.get("name")
        email = user.get("email")
        print(f"Ad: {name}\nEmail: {email}\n")


def fetch_and_print_user_names_and_emails() -> None:
    try:
        users = fetch_users(USERS_API_URL)
        print_user_names_and_emails(users)
    except requests.RequestException as e:
        print(f"API isteği sırasında hata oluştu: {e}")


if __name__ == "__main__":
    fetch_and_print_user_names_and_emails()
