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
  args = { "-e" },
}

dap.adapters.firefox = {
  type = "executable",
  command = "node",
  args = { vim.fn.stdpath("data") .. "/mason/packages/firefox-debug-adapter/dist/adapter.bundle.js" },
}

dap.configurations.typescript = {
  {
    name = "Launch Firefox",
    type = "firefox",
    request = "launch",
    url = "http://localhost:4200",
    webRoot = "${workspaceFolder}/web",
    firefoxExecutable = "/usr/bin/firefox",
    profile = "debug",
    keepProfileChanges = true,
  }
}

require("dap-python").setup(vim.fn.getcwd() .. "/venv/bin/python", { console = "externalTerminal" })

table.insert(dap.configurations.python, {
  type = "python",
  request = "launch",
  name = "API",
  program = "api",
  args = { "--no-debug" },
  console = "externalTerminal",
})

table.insert(dap.configurations.python, {
  type = "python",
  request = "launch",
  name = "Watchdog",
  program = "core",
  console = "externalTerminal",
})
