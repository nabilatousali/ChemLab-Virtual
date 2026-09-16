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

    def clean(self):
        cleaned_data = super().clean()

        email = cleaned_data.get("email")
        password = cleaned_data.get("password")

        if email and password:
            try:
                user_by_email = User.objects.get(
                    email__iexact=email.strip()
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
                username=user_by_email.username,
                password=password,
            )

            if self.user is None:
                raise forms.ValidationError(
                    "Adresse e-mail ou mot de passe incorrect."
                )

            if not self.user.is_active:
                raise forms.ValidationError(
                    "Ce compte est désactivé."
                )

        return cleaned_data
