require 'torch'
require 'nn'

require 'LanguageModel'

-- local ev = require'ev'


local cmd = torch.CmdLine()
cmd:option('-checkpoint', '/home/ubuntu/models/badr02_84000.t7')
cmd:option('-length', 128)
cmd:option('-start_text', '')
cmd:option('-sample', 1)
cmd:option('-temperature', 0.5)
cmd:option('-gpu', 0)
cmd:option('-gpu_backend', 'cuda')
cmd:option('-verbose', 0)
local opt = cmd:parse(arg)

-- String Splitter

function string:split(sSeparator, nMax, bRegexp)
  assert(sSeparator ~= '')
  assert(nMax == nil or nMax >= 1)

  local aRecord = {}

  if self:len() > 0 then
    local bPlain = not bRegexp
    nMax = nMax or -1

    local nField, nStart = 1, 1
    local nFirst,nLast = self:find(sSeparator, nStart, bPlain)
    while nFirst and nMax ~= 0 do
      aRecord[nField] = self:sub(nStart, nFirst-1)
      nField = nField+1
      nStart = nLast+1
      nFirst,nLast = self:find(sSeparator, nStart, bPlain)
      nMax = nMax-1
    end
    aRecord[nField] = self:sub(nStart)
  end

  return aRecord
end


local checkpoint = torch.load(opt.checkpoint)
local model = checkpoint.model

local msg
if opt.gpu >= 0 and opt.gpu_backend == 'cuda' then
  require 'cutorch'
  require 'cunn'
  cutorch.setDevice(opt.gpu + 1)
  model:cuda()
  msg = string.format('Running with CUDA on GPU %d', opt.gpu)
elseif opt.gpu >= 0 and opt.gpu_backend == 'opencl' then
  require 'cltorch'
  require 'clnn'
  model:cl()
  msg = string.format('Running with OpenCL on GPU %d', opt.gpu)
else
  msg = 'Running in CPU mode'
end
if opt.verbose == 1 then print(msg) end

model:evaluate()

print("READY")

-- Message Queue Stuff Starts Here

rb = require('amqp-util')

conn = rb.connect_rabbit{host="localhost"}
rb.declare_queue(conn, "CaptionToExpand")
rb.declare_queue(conn, "Expansions")

math.randomseed(os.time())

function expand_caption(consumer_tag, hash_caption)
  local hash, caption = unpack(string.split(hash_caption, '#', 1))

  opt.start_text = caption
  opt.temperature = math.random(40,69)/100
  opt.length = string.len(caption)+128

  function sample_model()
    return model:sample(opt)
  end

  err, sample = pcall(sample_model)
  
  -- print(sample)

  local rmq_opt = {}
  rmq_opt.routingkey = 'Expansions'
  local hash_sample = hash .. '#' .. sample
  rb.publish(conn, "", hash_sample, rmq_opt)
end

rb.wait_for_messages(conn, { CaptionToExpand = {expand_caption, {no_ack=1}} })


