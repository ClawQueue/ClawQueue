import DefaultTheme from 'vitepress/theme'
import { h } from 'vue'
import { useData } from 'vitepress'
import HomePage from './components/HomePage.vue'
import './style.css'

export default {
  ...DefaultTheme,
  Layout() {
    const { frontmatter } = useData()
    if (frontmatter.value.layout === 'home') {
      return h(HomePage)
    }
    return h(DefaultTheme.Layout)
  }
}
