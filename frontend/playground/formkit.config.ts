import { defineFormKitConfig } from '@formkit/vue'
import { rootClasses } from 'assets/themes/formkit.theme'
import { createProPlugin, dropdown, togglebuttons } from '@formkit/pro'
import { createAutoAnimatePlugin } from '@formkit/addons'
import { plugin, defaultConfig } from '@formkit/vue'


const fk_license_key = process.env.FORMKIT_PRO_LICENSE_KEY ? process.env.FORMKIT_PRO_LICENSE_KEY : 'fk-000000000'
const proPlugin = createProPlugin("fk-813909083ee", {
    dropdown,
    togglebuttons
    // any other Pro Inputs
})


export default defineFormKitConfig({
    config: {
        rootClasses
    },
    plugins: [proPlugin,
        createAutoAnimatePlugin(
            {
                /* optional AutoAnimate config */
                // default:
                duration: 250,
                easing: 'ease-in-out',
            },
            {
                /* optional animation targets object */
                // default:
                global: ['outer', 'inner'],
                form: ['form'],
                repeater: ['items'],
            }
        )
    ],
    // rules: {},
    // locales: {},
    // etc.
})