import torch
import torch.nn as nn

device = "cuda"

x = torch.rand(1000, 1, device = device) * 10
y = 3 * x + 2 + torch.randn_like(x) * 0.5

model  = nn.Linear(1, 1).to(device)

loss_fn = nn.MSELoss()
optimizer = torch.optim.SGD(model.parameters(), lr = 0.01)

for step in range(2000):
	pred = model(x)
	loss = loss_fn(pred, y)
	optimizer.zero_grad()
	loss.backward()
	optimizer.step()

	if step % 200 == 0:
		print(f'step: {step}, loss: {loss.item():.2f}')

print("w =", model.weight.item(), "| b =", model.bias.item())
