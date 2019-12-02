from locust import HttpLocust, TaskSet, between, task


import locust.stats

locust.stats.CSV_STATS_INTERVAL_SEC = 5 # default is 2 seconds

def login(l):
    l.client.post("/login", {"username":"a", "password":"a"})

def logout(l):
    l.client.get("/logout")

def index(l):
    l.client.get('/')
    
def additem(l):
    # l.client.get("/")
    l.client.post("/additem", {"content":"Stuff"})




class UserBehavior(TaskSet):
    tasks = {index: 2}
    
    def on_start(self):
        login(self)

    def on_stop(self):
        logout(self)

        
        
class WebsiteUser(HttpLocust):
    task_set = UserBehavior
    wait_time = between(1.0, 2.0) # how long to wait between requests
    

# locust -f load_tester.py --no-web --run-time 1m -c 1000 -r 5000 --host http://localhost
# Command to run the load_tester file, with no web ui, with 1090 concurrent users, at a hatch rate of 500/s


# locust -f load_tester.py -c 1000 -r 5000 --host http://130.245.168.47
# Command to run load_tester file, on another VM, from the web interface, port 8089
