/** Navigation 타입 */

export type PageView = 'chat' | 'admin' | 'scenarios' | 'log-settings'

export interface NavItem {
  view: PageView
  icon: string
  label: string
  path: string
}
