from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.models import User


class RegisterForm(forms.ModelForm):
    password = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput(
            attrs={
                "class": "auth-input",
                "placeholder": "Entrez votre mot de passe",
                "autocomplete": "new-password",
            }
        ),
    )

    password_confirmation = forms.CharField(
        label="Confirmer le mot de passe",
        widget=forms.PasswordInput(
            attrs={
                "class": "auth-input",
                "placeholder": "Confirmez votre mot de passe",
                "autocomplete": "new-password",
            }
        ),
    )

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "username",
            "email",
        ]

        labels = {
            "first_name": "Prénom",
            "last_name": "Nom",
            "username": "Nom d'utilisateur",
            "email": "Adresse e-mail",
        }

        widgets = {
            "first_name": forms.TextInput(
                attrs={
                    "class": "auth-input",
                    "placeholder": "Entrez votre prénom",
                }
            ),
            "last_name": forms.TextInput(
                attrs={
                    "class": "auth-input",
                    "placeholder": "Entrez votre nom",
                }
            ),
            "username": forms.TextInput(
                attrs={
                    "class": "auth-input",
                    "placeholder": "Choisissez un nom d'utilisateur",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "auth-input",
                    "placeholder": "Entrez votre adresse e-mail",
                    "autocomplete": "email",
                }
            ),
        }

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "Cette adresse e-mail est déjà utilisée."
            )

        return email

    def clean(self):
        cleaned_data = super().clean()

        password = cleaned_data.get("password")
        confirmation = cleaned_data.get("password_confirmation")

        if password and confirmation and password != confirmation:
            raise forms.ValidationError(
                "Les deux mots de passe ne correspondent pas."
            )

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)

        user.email = user.email.lower()
        # Le compte reste inactif jusqu'au clic sur le lien d'activation.
        user.is_active = False
        user.set_password(self.cleaned_data["password"])

        if commit:
            user.save()

        return user


class LoginForm(forms.Form):
    email = forms.EmailField(
        label="Adresse e-mail",
        widget=forms.EmailInput(
            attrs={
                "class": "auth-input",
                "placeholder": "Entrez votre adresse e-mail",
                "autocomplete": "email",
            }
        ),
    )

    password = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput(
            attrs={
                "class": "auth-input",
                "placeholder": "Entrez votre mot de passe",
                "autocomplete": "current-password",
            }
        ),
    )

    def __init__(self, *args, request=None, **kwargs):
        # La requête est transmise à authenticate() pour qu'axes
        # puisse attribuer chaque tentative (compte + IP).
        self.request = request
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()

        email = cleaned_data.get("email")
        password = cleaned_data.get("password")

        if email and password:
            try:
                user_by_email = User.objects.get(
                    email__iexact=email.strip().lower()
                )
            except User.DoesNotExist:
                raise forms.ValidationError(
                    "Adresse e-mail ou mot de passe incorrect."
                )
            except User.MultipleObjectsReturned:
                raise forms.ValidationError(
                    "Cette adresse e-mail est associée à plusieurs comptes."
                )

            self.user = authenticate(
                self.request,
                username=user_by_email.username,
                password=password,
            )

            if self.user is None:
                if not user_by_email.is_active:
                    raise forms.ValidationError(
                        "Ce compte n'est pas encore activé. "
                        "Vérifiez votre boîte e-mail."
                    )
                raise forms.ValidationError(
                    "Adresse e-mail ou mot de passe incorrect."
                )

        return cleaned_data
