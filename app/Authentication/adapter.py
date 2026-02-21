from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
# from allauth.account.adapter import DefaultAccountAdapter

# writing a custom adapter to save the role of the user during social login/signup
class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        # 1. Get role from session (set by frontend before redirecting to Google)
        # or default to pathfinder'
        selected_role = request.session.get('register_role', 'pathfinder')
        
        user.role = selected_role
        user.is_email_verified = True
        user.save() 
        return user

# class NoSignupAccountAdapter(DefaultAccountAdapter):
#     def is_open_for_signup(self, request):
#         return False
    
