from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from billing.plan_limits import get_plan_limits, validate_check_interval, can_add_monitor
from projects.models import Project
from monitors.models import Monitor

User = get_user_model()

class LoginForm(forms.Form):
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'Имя пользователя'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control', 'placeholder': 'Пароль'
    }))


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={
        'class': 'form-control', 'placeholder': 'Email'
    }))

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            if field_name == 'username':
                field.widget.attrs['placeholder'] = 'Имя пользователя'


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'description', 'status_page_enabled', 'status_page_title', 'status_page_logo']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Название проекта'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Описание...'}),
            'status_page_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'status_page_title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Заголовок статус-страницы'}),
            'status_page_logo': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://example.com/logo.png'}),
        }


class MonitorForm(forms.ModelForm):
    class Meta:
        model = Monitor
        fields = [
            'project', 'name', 'url', 'monitor_type', 
            'check_interval', 'timeout', 'retries', 
            'ssl_enabled', 'ssl_expiry_threshold'
        ]
        widgets = {
            'project': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Мой Сайт'}),
            'url': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'example.com или https://example.com'}),
            'monitor_type': forms.Select(attrs={'class': 'form-select'}),
            'check_interval': forms.NumberInput(attrs={'class': 'form-control', 'min': 30}),
            'timeout': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 60}),
            'retries': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 10}),
            'ssl_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ssl_expiry_threshold': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if user:
            self.fields['project'].queryset = Project.objects.filter(user=user)
            limits = get_plan_limits(user)
            self.fields['check_interval'].widget.attrs['min'] = limits['min_interval']
            self.fields['check_interval'].help_text = (
                f"Минимум {limits['min_interval']} сек. для вашего тарифа"
            )

    def clean_check_interval(self):
        interval = self.cleaned_data['check_interval']
        if self.user:
            ok, err = validate_check_interval(self.user, interval)
            if not ok:
                raise forms.ValidationError(err)
        return interval
