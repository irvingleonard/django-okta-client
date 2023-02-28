from django.contrib.auth.base_user import BaseUserManager


class OktaUserManager(BaseUserManager):
	'''Okta user manager
	Custom user manager to work with the Okta user model.
	'''
	
	use_in_migrations = True
	
	def create_user(self, login, email, firstName, lastName, password = None, **other_fields):
		'''Create a local user
		Create and save a user with the provided details.
		'''
		
		try:
			email = self.normalize_email(email)
		except Exception:
			pass
		
		user = self.model(login = login, email = email, firstName = firstName, lastName = lastName, **other_fields)
		user.set_unusable_password()
		user.save()
		
		return user

	def create_superuser(self, login, email, firstName, lastName, password = None, **other_fields):
		'''Create a local superuser
		Create and save a superuser with the provided details, including a password.
		'''
			
		try:
			email = self.normalize_email(email)
		except Exception:
			pass
		
		other_fields.setdefault('is_staff', True)
		other_fields.setdefault('is_superuser', True)
		other_fields.setdefault('is_active', True)

		if other_fields.get('is_staff') is not True:
			raise ValueError('Superuser must have is_staff=True.')
		if other_fields.get('is_superuser') is not True:
			raise ValueError('Superuser must have is_superuser=True.')
		
		user = self.model(login = login, email = email, firstName = firstName, lastName = lastName, **other_fields)
		user.set_password(password)
		user.save()
		
		return user
