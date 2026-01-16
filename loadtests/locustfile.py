from loadtests.users.analysis import AnalysisUser
from loadtests.users.device import DeviceUser
from loadtests.users.login import LoginUser
from loadtests.users.logout import LogoutUser
from loadtests.users.profile import ProfileUser
from loadtests.users.register import RegistrationUser
from loadtests.users.social import SocialUser
from loadtests.users.waitlist import WaitlistUser

# Set wait times and weights if needed centrally
AnalysisUser.weight = 1
WaitlistUser.weight = 2
ProfileUser.weight = 3
DeviceUser.weight = 1
LoginUser.weight = 2
LogoutUser.weight = 1
RegistrationUser.weight = 2
SocialUser.weight = 1

# Optional: Set a common host if not provided in command line
