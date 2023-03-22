vim.fn.jobstart("ng serve -c development --host 0.0.0.0", { cwd = "web" })

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
  preferences = {
    ["signon.rememberSignons"] = true,
  },
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
  justMyCode = false,
}
table.insert(dap.configurations.python, api)

local watchdog = {
  type = "python",
  request = "launch",
  name = "Watchdog",
  program = "core",
  console = "externalTerminal",
  justMyCode = false,
}
table.insert(dap.configurations.python, watchdog)

dap.run(typescript)
dap.run(watchdog)
dap.run(api)

local sliver = vim.fn.stdpath("config") .. "/sessions/sliver"
if vim.fn.filereadable(sliver) == 1 then
  vim.cmd("source " .. sliver)
end
