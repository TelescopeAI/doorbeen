<script setup lang="ts">

import {SignedIn, SignedOut, SignInButton, useAuth, UserButton} from "vue-clerk";
const {
  isSignedIn,
} = useAuth()
</script>

<template>
  <div>
    <header v-if="isSignedIn">
      <SignedIn>
        <UserButton afterSignOutUrl="/auth/login" afterMultiSessionSingleSignOutUrl="/auth/login"/>
      </SignedIn>
      <SignedOut>
        <SignInButton/>
      </SignedOut>
    </header>
  </div>
</template>

<style scoped>

</style>