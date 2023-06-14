local dap = require("dap")

-- dap.defaults.fallback.force_external_terminal = true
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
  reAttach = true,
  preferences = {
    ["signon.rememberSignons"] = true,
  },
}
dap.configurations.typescript = {
  typescript,
}

require("dap-python").setup(vim.fn.getcwd() .. "/.venv/bin/python", { console = "externalTerminal", justMyCode = false })

local api = {
  type = "python",
  request = "launch",
  name = "API",
  module = "sliver.api",
  console = "externalTerminal",
  justMyCode = false,
}
table.insert(dap.configurations.python, api)

local watchdog = {
  type = "python",
  request = "launch",
  name = "Watchdog",
  module = "sliver",
  console = "externalTerminal",
  justMyCode = false,
}
table.insert(dap.configurations.python, watchdog)

local sliver = vim.fn.stdpath("config") .. "/sessions/sliver"
if vim.fn.filereadable(sliver) == 1 then
  vim.ui.input({ prompt = "Load session " .. sliver .. "? [Y|n]  > " }, function(input)
    if input == "n" then
      return
    end
    vim.cmd("source " .. sliver)
  end)
end

vim.ui.input({ prompt = "Run debugger sessions? [Y|n]  > " }, function(input)
  if input == "n" then
    return
  end
  -- vim.fn.jobstart("ng serve -c development --host 0.0.0.0", { cwd = "web" })
  dap.run(typescript)
  -- dap.run(watchdog)
  dap.run(api)
end)
