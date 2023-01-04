lua << EOF
require("lspconfig").pylsp.setup({
  -- organizeImports requires pylsp-rope in mason env
  on_attach = LSPAttach,
  capabilities = LSPCapabilities,
  settings = {
    pylsp = {
      plugins = {
        mccabe = {
          threshold = 20,
        },
      },
    },
  },
})

require("dap").adapters.chrome = {
  type = "executable",
  command = "node",
  args = { vim.fn.stdpath("data") .. "/mason/packages/chrome-debug-adapter/out/src/chromeDebug.js" },
}
require("dap").configurations.typescript = {
  {
    type = "chrome",
    request = "attach",
    program = "${file}",
    cwd = vim.fn.getcwd(),
    sourceMaps = true,
    protocol = "inspector",
    port = 9222,
    webRoot = "${workspaceFolder}/web",
  },
}

require("dap").adapters.python = {
  type = "executable";
  command = vim.fn.getcwd() .. "/.venv/bin/python3";
  args = { "-m", "debugpy.adapter" };
}
require("dap").configurations.python = {
  {
    type = "python",
    request = "launch",
    name = "Stream",
    program = vim.fn.getcwd() .. "/.venv/bin/stream",
  },
  {
    type = "python",
    request = "launch",
    name = "Watch",
    program = vim.fn.getcwd() .. "/.venv/bin/watch",
  },
  {
    type = "python",
    request = "launch",
    name = "Serve",
    program = vim.fn.getcwd() .. "/.venv/bin/serve",
  },
}
EOF
