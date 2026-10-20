from locust import HttpUser, task, between

class OpenBmcUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        self.client.auth = ("root", "0penBmc")
        self.client.verify = False

    @task
    def get_info(self):
        self.client.get("https://127.0.0.1:2443/redfish/v1/Systems/system")

    @task
    def get_powerstate(self):
        response = self.client.get("https://127.0.0.1:2443/redfish/v1/Systems/system")
        if response.status_code == 200:
            data = response.json()
            power_state = data.get("PowerState")
            print(f"Power State: {power_state}")
    
class PublicApiUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def get_placeholder_posts(self):
        self.client.get("https://jsonplaceholder.typicode.com/posts")
    
    @task
    def get_weather(self):
        self.client.get("https://wttr.in/Novosibirsk?format=j1")