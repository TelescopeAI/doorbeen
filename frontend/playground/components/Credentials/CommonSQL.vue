<script setup lang="ts">
const handleIconClick = (node, e) => {
  node.props.suffixIcon = node.props.suffixIcon === 'eye' ? 'eyeClosed' : 'eye'
  node.props.type = node.props.type === 'password' ? 'text' : 'password'
}



const props = defineProps({
  host: {
    type: String,
    default: "localhost"
  },
  port: {
    type: Number,
    default: 5432
  },
  username: {
    type: String,
    default: "root"
  },
  password: {
    type: String,
    default: "password"
  },
  database: {
    type: String,
    default: "public"
  }
})

const form_defaults = {
  host: "localhost",
  port: 5432,
  username: "root",
  password: "password",
  database: "public"

}
</script>

<template>
  <FormKit
      label="Host"
      name="host"
      type="text"
      help="Where is the database located?"
      outer-class="max-w-full"
      :value="props.host"

  />
  <FormKit
      label="Port"
      name="port"
      type="text"
      help="What port is the database running on? (default: 5432 for PostgreSQL)"
      outer-class="max-w-full"
      :value="props.port"
  />

  <FormKit
      label="Username"
      name="username"
      type="text"
      help="What is the username?"
      outer-class="max-w-full"
      :value="props.username"
  />
  <FormKit
      label="Password"
      name="password"
      type="password"
      help="What is the password?"
      outer-class="max-w-full"
      prefix-icon="password"
      suffix-icon="eyeClosed"
      @suffix-icon-click="handleIconClick"
      suffix-icon-class="hover:text-blue-500"
      :value="props.password"
  />
  <FormKit
      label="Database Name"
      name="database"
      type="text"
      help="What is the name of the database?"
      outer-class="max-w-full"
      :value="props.database"
  />
</template>

<style scoped>

</style>