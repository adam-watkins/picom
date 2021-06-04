<template>
  <v-card elevation="6">
    <v-card-header title="Settings" />
    <v-form v-model="isFormValid">
      <v-text-field
        class="mx-2"
        v-model="aeTitle"
        :rules="[validateAETitle]"
        counter
        :prefix="`Your AE Title is: ${$store.state.config.USER_AE_PREFIX}`"
        prepend-icon="mdi-access-point"
      />
    </v-form>
    <v-divider class="my-3" light />
    <v-card-actions class="justify-center">
      <v-icon-btn
        save
        :disabled="!(didEdit && isFormValid)"
        @click="submit"
        color="confirm"
      />
    </v-card-actions>
  </v-card>
</template>

<script>
import { mapState } from 'vuex'
import { generic_get } from '~/api'
import { validateAETitle } from '~/utilities/validationRules'

export default {
  data() {
    return {
      isFormValid: false,
      aeTitle: '',
      currentAETitle: ''
    }
  },
  computed: {
    ...mapState('auth', ['user']),
    ...mapState('users', ['users']),
    didEdit() {
      return this.currentAETitle !== this.aeTitle
    }
  },
  created() {
    this.getUserInfo()
    this.$store.dispatch('users/fetchUsers')
  },
  methods: {
    validateAETitle,
    async getUserInfo() {
      const URL = '/user/me'
      const { ae_title } = await generic_get(this, URL)
      this.aeTitle = ae_title
      this.currentAETitle = ae_title
    },
    async saveUserAETitle() {
      const res = await this.$store.dispatch('users/editUserSettings', {
        id: this.user.id,
        ae_title: this.aeTitle,
        access_allowed: this.user.access_allowed,
        is_admin: this.user.is_admin
      })
      this.currentAETitle = res.ae_title
    },
    submit() {
      try {
        if (this.user.ae_title !== this.ae_title) {
          this.saveUserAETitle()
        }
        this.$toaster.toastSuccess('Changes saved!')
      } catch (e) {
        this.$toaster.toastError('Could not save changes')
      }
    }
  }
}
</script>
