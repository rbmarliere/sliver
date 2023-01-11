require("lspconfig").pylsp.setup({
  -- organizeImports requires pylsp-rope in mason env
  on_attach = LSPAttach,
  capabilities = LSPCapabilities,
  settings = {
    pylsp = {
      plugins = {
        mccabe = {
          threshold = 25,
        },
      },
    },
  },
})

-- require("dap").set_log_level("TRACE")

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

local cfg = function(config, on_config)
  local final_config = vim.deepcopy(config)
  final_config.justMyCode = false
  on_config(final_config)
end;

require("dap").adapters.pyscript = {
  type = "executable";
  command = vim.fn.getcwd() .. "/venv/bin/python3";
  args = { "-m", "debugpy.adapter" };
}
require("dap").adapters.interpreter = {
  type = "server";
  port = 33332;
  enrich_config = cfg
}
require("dap").adapters.serve = {
  type = "server";
  port = 33333;
  enrich_config = cfg;
}
require('dap').defaults.serve.exception_breakpoints = {}
require("dap").adapters.stream = {
  type = "server";
  port = 33334;
  enrich_config = cfg;
}
require("dap").adapters.watch = {
  type = "server";
  port = 33335;
  enrich_config = cfg
}

require("dap").configurations.python = {
  {
    type = "pyscript",
    request = "launch",
    name = "Launch File",
    program = "${file}";
    args = function()
      local argument_string = vim.fn.input('args: ')
      return vim.fn.split(argument_string, " ", true)
    end,
  },
  {
    type = "interpreter",
    request = "attach",
    name = "Attach to Interpreter",
  },
  {
    type = "serve",
    request = "attach",
    name = "Serve",
  },
  {
    type = "stream",
    request = "attach",
    name = "Stream",
  },
  {
    type = "watch",
    request = "attach",
    name = "Watch",
  },
}
