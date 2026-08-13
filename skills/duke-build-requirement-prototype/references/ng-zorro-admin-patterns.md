# NG-ZORRO 后台原型指南

## 适用优先级

- 新建后台管理、运营或配置页面且没有既有设计体系时，高优先采用 NG-ZORRO 18.2.x。
- 既有页面、参考截图、用户指定体系和产品一致性高于该默认项。
- 移动端、营销页和非后台页面不默认套用 NG-ZORRO。
- 官方基准：[NG-ZORRO 18.2.x 介绍](https://ng.ant.design/version/18.2.x/docs/introduce/zh)。

## 技术形态

| 原型形态 | 处理方式 |
| --- | --- |
| 单文件HTML | 使用原生HTML、内联CSS和原生JavaScript复刻组件语义、状态和视觉规范，不加载 Angular 或远程组件资源 |
| 既有Angular 18原型工程 | 使用 `ng-zorro-antd@18.2.x`，沿用工程构建、主题和组件引入方式 |
| 非Angular工程 | 保持现有技术栈，只借鉴NG-ZORRO交互模式，不强行迁移框架 |

不要只为套用组件库创建 Angular 工程，也不要把需求原型扩展为生产前端。

## 组件映射

| 页面需求 | 优先组件语义 |
| --- | --- |
| 应用框架 | `nz-layout`、`nz-sider`、`nz-header`、`nz-content` |
| 导航与定位 | `nz-menu`、`nz-breadcrumb`、`nz-page-header` |
| 查询和录入 | `nz-form`、`nz-input`、`nz-select`、`nz-date-picker`、`nz-switch`、`nz-checkbox`、`nz-radio` |
| 操作 | `nz-button` 的 primary、default、text、danger 状态 |
| 数据展示 | `nz-table`、`nz-pagination`、`nz-descriptions`、`nz-tag`、`nz-badge`、`nz-empty`、`nz-spin` |
| 分组与切换 | `nz-card`、`nz-tabs`、`nz-collapse`、`nz-segmented` |
| 详情和确认 | `nz-drawer`、`nz-modal`、`nz-popconfirm`、`nz-tooltip` |
| 结果反馈 | `nz-message`、`nz-notification`、`nz-alert`、`nz-result` |

只选择需求验证所需的组件，不为展示组件库完整度添加模块。

## 页面结构

1. 使用布局、菜单、面包屑和页面标题建立稳定的后台信息层级。
2. 列表页按“页面标题与主操作 → 查询区 → 批量操作 → 表格 → 分页”组织。
3. 详情内容较轻时使用抽屉；需要强确认或阻断操作时使用弹窗；复杂独立任务使用详情页。
4. 表单保持标签、必填、帮助、校验和错误信息的统一对齐。
5. 表格同时覆盖加载、空数据、筛选无结果、错误、分页和无权限等需求相关状态。

## 单文件HTML还原要求

- 使用 Ant Design 常用视觉令牌：主色 `#1677ff`、常规边框 `#d9d9d9`、圆角 `6px`、紧凑后台信息密度。
- 使用语义化HTML和可访问属性，不直接输出无法运行的 `nz-*` Angular 标签。
- 可使用 `ant-` 前缀类名表达组件映射，并在根节点标记 `data-design-system="ng-zorro-18.2.x"`。
- 对按钮、筛选项、抽屉、弹窗、分页和反馈实现需求验证所需的最小交互。
- 不从公共CDN加载脚本、字体或样式；原型必须在离线环境可打开。

## 交付说明

说明页面被判定为后台或非后台的依据、采用的组件体系、使用的关键组件语义，以及因既有产品一致性而偏离NG-ZORRO默认项的部分。
