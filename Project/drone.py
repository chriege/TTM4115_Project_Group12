import paho.mqtt.client as mqtt
from stmpy import Machine, Driver

##Pickup Handoff and In-Flight




class System: ## v2

    def order_confirmed(self):
        print("Order confirmed. Transitioning to selectPath.")

    def path_selected(self):
        print("Path selected. Transitioning to takeOff.")

    def takeoff_complete(self):
        print("Takeoff complete. Transitioning to inFlight.")

    def arrived_at_dropoff(self):
        print("Arrived at dropoff. Transitioning to landing.")

    def if_package(self):
        print("Package detected. Transitioning to delivery.")

    def package_delivered(self):
        print("Package delivered. Transitioning to selectPath.")

    def no_package(self):
        print("No package detected. Transitioning to idle.")

driver = Driver()
system = System()

transitions = [
    {'source':'initial', 'target':'idle'},
    {'source':'idle', 'target':'selectPath', 'trigger':'orderConfirmed'},
    {'source':'selectPath', 'target':'takeOff', 'trigger':'pathSelected'},
    {'source':'takeOff', 'target':'inFlight', 'trigger':'takeOffComplete'},
    {'source':'inFlight', 'target':'landing', 'trigger':'arrivedAtDropoff'},
    {'source':'landing', 'target':'delivery', 'trigger':'ifPackage'},
    {'source':'delivery', 'target':'selectPath','trigger':'packageDelivered'},
    {'source':'landing', 'target':'idle', 'trigger':'noPackage'},
]

stm_system = Machine(transitions=transitions, obj=system, name='stm_system')
system.stm = stm_system

driver.add_stm(stm_system)
driver.wait_until_finished()