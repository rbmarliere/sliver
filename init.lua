vim.fn.jobstart("ng serve -c development --host 0.0.0.0", { cwd = "web" })

require("lspconfig").pylsp.setup({
  -- organizeImports requires pylsp-rope in mason env
  on_attach = LSPAttach,
  capabilities = LSPCapabilities,
  settings = { pylsp = { plugins = { mccabe = { threshold = 25, }, }, }, },
})

local dap = require("dap")

dap.defaults.fallback.force_external_terminal = true

dap.defaults.fallback.external_terminal = {
  command = "/usr/local/bin/alacritty",
  args = { "--hold", "-e" },
}

dap.adapters.firefox = {
  type = "executable",
  command = "node",
  args = { vim.fn.stdpath("data") .. "/mason/packages/firefox-debug-adapter/dist/adapter.bundle.js" },
}

local typescript = {
  name = "Launch Firefox",
  type = "firefox",
  request = "launch",
  url = "http://localhost:4200",
  webRoot = "${workspaceFolder}/web",
  firefoxExecutable = "/usr/bin/firefox",
  profile = "debug",
  keepProfileChanges = true,
}
dap.configurations.typescript = {
  typescript,
}

require("dap-python").setup(vim.fn.getcwd() .. "/venv/bin/python", { console = "externalTerminal" })

local api = {
  type = "python",
  request = "launch",
  name = "API",
  program = "api",
  args = { "--no-debug" },
  console = "externalTerminal",
}
table.insert(dap.configurations.python, api)

local watchdog = {
  type = "python",
  request = "launch",
  name = "Watchdog",
  program = "core",
  console = "externalTerminal",
}
table.insert(dap.configurations.python, watchdog)

table.insert(dap.configurations.python, {
  type = "python",
  request = "launch",
  name = "Stream",
  program = "strategies/hypnox/twitter.py",
  console = "externalTerminal",
})

dap.run(typescript)
dap.run(api)
dap.run(watchdog)
