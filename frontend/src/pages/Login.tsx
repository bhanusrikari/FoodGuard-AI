import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { AuthLayout } from '@/components/layout/AuthLayout'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { useAuth } from '@/context/AuthContext'
import { useTranslation } from '@/i18n/LanguageContext'
import { loginSchema, type LoginFormValues } from '@/lib/schemas'
import { defaultRouteForRole } from '@/lib/roles'
import { toApiError } from '@/types/errors'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const t = useTranslation()
  const [formError, setFormError] = useState<string | null>(null)

  const registeredEmail = (location.state as { registeredEmail?: string } | null)?.registeredEmail
  const from = (location.state as { from?: Location } | null)?.from

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: registeredEmail ?? '', password: '' },
  })

  async function onSubmit(values: LoginFormValues) {
    setFormError(null)
    try {
      const user = await login(values)
      const target = from ? `${from.pathname}${from.search}` : defaultRouteForRole(user.role)
      navigate(target, { replace: true })
    } catch (error) {
      setFormError(toApiError(error).message)
    }
  }

  return (
    <AuthLayout title={t('auth.login.title')} subtitle={t('auth.login.subtitle')}>
      {registeredEmail && (
        <p className="mb-4 rounded-lg bg-success-50 px-3 py-2 text-sm text-success-700">
          {t('auth.login.accountCreated')}
        </p>
      )}
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
        <Input
          label={t('auth.login.email')}
          type="email"
          autoComplete="email"
          required
          error={errors.email?.message}
          {...register('email')}
        />
        <Input
          label={t('auth.login.password')}
          type="password"
          autoComplete="current-password"
          required
          error={errors.password?.message}
          {...register('password')}
        />
        {formError && (
          <p role="alert" className="text-sm text-danger-600">
            {formError}
          </p>
        )}
        <Button type="submit" className="w-full" isLoading={isSubmitting}>
          {t('auth.login.submit')}
        </Button>
      </form>
      <p className="mt-6 text-center text-sm text-neutral-500">
        {t('auth.login.noAccount')}{' '}
        <Link to="/register" className="font-medium text-primary-700 hover:underline">
          {t('auth.login.createOne')}
        </Link>
      </p>
    </AuthLayout>
  )
}
